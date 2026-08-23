from pathlib import Path
import json
import base64
import os
import secrets
from datetime import datetime
import pandas as pd
from dash import Dash, Input, Output, State, dash_table, dcc, html, ctx, ALL
from dash.exceptions import PreventUpdate
from dash import no_update
from flask import Response, has_request_context, request, session
from industry_map import derive_industry


# ── Local environment and access protection ─────────────────────────────────
def load_local_env():
    """Load simple KEY=VALUE settings from the ignored local .env file."""
    env_file = Path(__file__).with_name(".env")
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


load_local_env()
ACCESS_PASSWORD = os.getenv("DASH_ACCESS_PASSWORD")
SESSION_SECRET = os.getenv("DASH_SESSION_SECRET") or secrets.token_urlsafe(32)

if not ACCESS_PASSWORD:
    raise RuntimeError(
        "DASH_ACCESS_PASSWORD is not set. Add it to the local .env file "
        "before starting the dashboard."
    )

# ── Paths ────────────────────────────────────────────────────────────────────
DATA_FILE = Path(__file__).with_name("Merged_Business_Data.csv")
FAVOURITES_FILE = DATA_FILE.with_name("favourites.json")
COMMENTS_FILE = DATA_FILE.with_name("comments.json")
LOGO_FILE = DATA_FILE.with_name("Keystone Logo (small).png")

# ── Persistence helpers ──────────────────────────────────────────────────────
def load_favourites():
    if FAVOURITES_FILE.exists():
        try:
            with open(FAVOURITES_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_favourites(favs):
    with open(FAVOURITES_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(favs)), f, indent=2)

def load_comments():
    if COMMENTS_FILE.exists():
        try:
            with open(COMMENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_comments(comments):
    with open(COMMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(comments, f, indent=2, ensure_ascii=False)

# ── Logo helper ──────────────────────────────────────────────────────────────
def encode_logo(path):
    try:
        with open(path, "rb") as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    except Exception:
        return None

logo_src = encode_logo(LOGO_FILE)

# ── Load CSV ─────────────────────────────────────────────────────────────────
businesses = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
businesses.columns = businesses.columns.str.strip()
businesses = businesses.replace({"(blank)": "", "blank": ""}).fillna("")

# Exclude permanently closed businesses
businesses = businesses[businesses["Permanently Closed"].astype(str).str.lower() != "true"]

# Ensure numeric columns are numeric
for col in ["Reviews Count", "Total Score"]:
    if col in businesses.columns:
        businesses[col] = pd.to_numeric(businesses[col], errors="coerce")

if "Favourite" not in businesses.columns:
    businesses["Favourite"] = "No"

if "Industry" not in businesses.columns:
    businesses["Industry"] = ""
needs_industry = businesses["Industry"].astype(str).str.strip() == ""
businesses.loc[needs_industry, "Industry"] = businesses.loc[needs_industry, "Category"].apply(derive_industry)

required_columns = [
    "Business Name", "Phone", "Email", "Website", "Address",
    "Google Maps", "Category", "Suburb",
    "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun",
    "Assistive Hearing Loop", "Wheelchair Accessible Entrance",
    "Wheelchair Accessible Parking Lot", "Wheelchair Accessible Restroom",
    "Wheelchair Accessible Seating", "Reviews Count", "Total Score",
]
missing = [c for c in required_columns if c not in businesses.columns]
if missing:
    raise ValueError("Missing columns: " + ", ".join(missing))

# ── Helpers ──────────────────────────────────────────────────────────────────
def make_options(values):
    clean = sorted({str(v).strip() for v in values if str(v).strip()})
    return [{"label": v, "value": v} for v in clean]

ACCESSIBILITY_FEATURES = [
    "Assistive Hearing Loop",
    "Wheelchair Accessible Entrance",
    "Wheelchair Accessible Parking Lot",
    "Wheelchair Accessible Restroom",
    "Wheelchair Accessible Seating",
]

REVIEW_COUNT_OPTIONS = [
    {"label": "Less than 50", "value": "Less than 50"},
    {"label": "50-200", "value": "50-200"},
    {"label": "200+", "value": "200+"},
]


def apply_filters(
    data,
    search=None,
    industry=None,
    category=None,
    suburb=None,
    accessibility=None,
    review_count=None,
    favourites_only=None,
    fav_set=None,
    ignore=None,
):
    filtered = data.copy()
    ignore = ignore or set()

    if search and "search" not in ignore:
        filtered = filtered[
            filtered["Business Name"]
            .astype(str)
            .str.contains(search.strip(), case=False, na=False, regex=False)
        ]
    if industry and "industry" not in ignore:
        filtered = filtered[filtered["Industry"] == industry]
    if category and "category" not in ignore:
        filtered = filtered[filtered["Category"] == category]
    if suburb and "suburb" not in ignore:
        filtered = filtered[filtered["Suburb"] == suburb]
    if accessibility and "accessibility" not in ignore:
        for feature in accessibility:
            if feature in filtered.columns:
                filtered = filtered[filtered[feature] == True]
    if review_count and "review_count" not in ignore:
        if review_count == "Less than 50":
            filtered = filtered[filtered["Reviews Count"] < 50]
        elif review_count == "50-200":
            filtered = filtered[
                (filtered["Reviews Count"] >= 50) &
                (filtered["Reviews Count"] <= 200)
            ]
        elif review_count == "200+":
            filtered = filtered[filtered["Reviews Count"] > 200]
    if favourites_only == "yes" and "favourites" not in ignore and fav_set is not None:
        filtered = filtered[filtered["Business Name"].isin(fav_set)]
    return filtered

TABLE_COLS = ["Business Name", "Phone", "Website", "Suburb", "Industry"]

app = Dash(__name__)
app.title = "Keystone Employer Database"
server = app.server
server.secret_key = SESSION_SECRET


PUBLIC_PATHS = {
    "/",
    "/_dash-layout",
    "/_dash-dependencies",
    "/_dash-config",
    "/_favicon.ico",
}


def _is_login_callback():
    """Allow the callback that verifies the password before a session exists."""
    if request.path != "/_dash-update-component" or request.method != "POST":
        return False

    payload = request.get_json(silent=True) or {}
    output = str(payload.get("output", ""))
    if "auth-session" in output:
        return True

    outputs = payload.get("outputs") or []
    return any("auth-session" in str(item) for item in outputs)


@app.server.before_request
def protect_dashboard():
    path = request.path
    if (
        path in PUBLIC_PATHS
        or path.startswith("/_dash-component-suites/")
        or path.startswith("/assets/")
        or _is_login_callback()
        or session.get("authenticated") is True
    ):
        return None

    return Response("Authentication required.", 401)


app.index_string = """
<!DOCTYPE html>
<html>
    <head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
    <style>
        html, body, #react-entry-point { margin: 0; min-height: 100%; background: #4200A8; }
        * { box-sizing: border-box; }
        .dash-table-container a {
            display: inline-block;
            background: #66F2E3;
            color: #2E1654;
            padding: 6px 14px;
            border-radius: 20px;
            text-decoration: none;
            font-weight: bold;
            font-size: 13px;
            transition: transform 0.1s, box-shadow 0.1s;
        }
        .dash-table-container a:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .dash-spreadsheet-menu {
            display: none !important;
        }
        .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td {
            cursor: pointer;
        }
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.6);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .modal-card {
            background: white;
            border-radius: 20px;
            max-width: 800px;
            width: 100%;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 20px 50px rgba(0,0,0,0.3);
        }
    </style></head>
    <body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body>
</html>
"""

dashboard_layout = html.Div(
    style={"backgroundColor": "#4200A8", "minHeight": "100vh", "fontFamily": "Arial, sans-serif", "margin": "0", "paddingBottom": "70px"},
    children=[
        dcc.Store(id="current-business-store", storage_type="memory"),
        dcc.Store(id="fav-update-trigger", data=0),
        dcc.Store(id="comment-update-trigger", data=0),

        # ── Header ───────────────────────────────────────────────────────────
        html.Div(
            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "padding": "25px 45px", "borderBottom": "1px solid rgba(255,255,255,0.15)"},
            children=[
                html.Img(src=logo_src, style={"height": "55px"}) if logo_src else html.H1("Keystone Employer Database", style={"color": "#66F2E3", "margin": "0", "fontSize": "32px"}),
                html.Div(
                    style={"display": "flex", "alignItems": "center", "gap": "16px"},
                    children=[
                        html.A(
                            "🌐 keystone.org.au",
                            href="https://www.keystone.org.au/",
                            target="_blank",
                            style={"color": "white", "fontSize": "16px", "fontWeight": "bold", "textDecoration": "none"},
                        ),
                        html.Button(
                            "Log out",
                            id="logout-btn",
                            n_clicks=0,
                            style={
                                "backgroundColor": "transparent",
                                "color": "white",
                                "border": "1px solid #66F2E3",
                                "borderRadius": "20px",
                                "padding": "8px 15px",
                                "fontSize": "14px",
                                "fontWeight": "bold",
                                "cursor": "pointer",
                            },
                        ),
                    ],
                ),
            ],
        ),

        # ── Main Content ─────────────────────────────────────────────────────
        html.Div(
            style={"maxWidth": "1500px", "margin": "0 auto", "padding": "45px 30px"},
            children=[
                html.H2("🔍 Find the right businesses and opportunities", style={"color": "white", "fontSize": "36px", "marginBottom": "10px"}),
                html.P("Search by business name and filter the available results.", style={"color": "#D9CCFF", "fontSize": "18px", "marginBottom": "30px"}),

                # ── Filter Card ──────────────────────────────────────────────
                html.Div(
                    style={"backgroundColor": "white", "borderRadius": "20px", "padding": "28px", "boxShadow": "0 12px 30px rgba(0,0,0,0.20)", "marginBottom": "30px"},
                    children=[
                        html.Label("🔍 Search businesses", style={"fontWeight": "bold", "color": "#2E1654"}),
                        dcc.Input(
                            id="search-input", type="text", placeholder="Search by business name...",
                            debounce=True,
                            style={"width": "100%", "padding": "14px", "marginTop": "8px", "marginBottom": "20px", "borderRadius": "10px", "border": "1px solid #CCCCCC", "fontSize": "16px", "height": "48px"},
                        ),
                        html.Div(
                            style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(190px, 1fr))", "gap": "16px"},
                            children=[
                                html.Div(children=[
                                    dcc.Dropdown(id="industry-filter", placeholder="🏭 Industry", clearable=True),
                                    html.Div(
                                        id="category-filter-wrapper",
                                        style={"display": "none"},
                                        children=[dcc.Dropdown(id="category-filter", placeholder="📂 Category", clearable=True)],
                                    ),
                                ]),
                                dcc.Dropdown(id="suburb-filter", placeholder="📍 Suburb", clearable=True),
                                dcc.Dropdown(
                                    id="accessibility-filter",
                                    placeholder="♿ Accessibility",
                                    clearable=True,
                                    multi=True,
                                ),
                                dcc.Dropdown(id="review-count-filter", placeholder="💬 Review count", clearable=True),
                                dcc.Dropdown(
                                    id="favourites-only-filter",
                                    placeholder="⭐ Favourites",
                                    clearable=True,
                                    options=[{"label": "⭐ Only favourites", "value": "yes"}],
                                ),
                            ],
                        ),
                    ],
                ),

                # ── Results Table ────────────────────────────────────────────
                html.Div(
                    style={"backgroundColor": "white", "borderRadius": "20px", "padding": "28px", "boxShadow": "0 12px 30px rgba(0,0,0,0.20)"},
                    children=[
                        html.H3("📋 Business results", style={"color": "#2E1654", "fontSize": "24px", "marginTop": "0"}),
                        html.Div(id="result-count", style={"color": "#6F5A8C", "marginBottom": "15px"}),
                        dash_table.DataTable(
                            id="business-table",
                            active_cell=None,
                            hidden_columns=["_row_idx"],
                            columns=[
                                {"name": col, "id": col, "presentation": "markdown" if col == "Website" else "input"}
                                for col in TABLE_COLS
                            ] + [{"name": "_row_idx", "id": "_row_idx"}],
                            page_size=10,
                            sort_action="native",
                            markdown_options={"link_target": "_blank"},
                            style_table={"overflowX": "auto", "borderRadius": "12px"},
                            style_header={"backgroundColor": "#66F2E3", "color": "#2E1654", "fontWeight": "bold", "border": "none", "padding": "12px"},
                            style_cell={"textAlign": "left", "padding": "12px", "border": "1px solid #EEEEEE", "fontFamily": "Arial, sans-serif", "minWidth": "125px", "maxWidth": "270px", "whiteSpace": "normal"},
                            style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#F8F5FF"}],
                        ),
                    ],
                ),
            ],
        ),

        # ── Modal Popup ──────────────────────────────────────────────────────
        html.Div(
            id="modal-overlay",
            style={"display": "none"},
            className="modal-overlay",
            children=[
                html.Div(
                    className="modal-card",
                    style={"padding": "28px", "position": "relative"},
                    children=[
                        html.Button(
                            "✕",
                            id="close-modal-btn",
                            n_clicks=0,
                            style={
                                "position": "absolute",
                                "top": "16px",
                                "right": "20px",
                                "background": "none",
                                "border": "none",
                                "fontSize": "20px",
                                "cursor": "pointer",
                                "color": "#666",
                            }
                        ),
                        html.Div(id="modal-content"),
                    ],
                ),
            ],
        ),
    ],
)


def _login_container_style(authenticated):
    return {
        "display": "none" if authenticated else "flex",
        "minHeight": "100vh",
        "backgroundColor": "#4200A8",
        "alignItems": "center",
        "justifyContent": "center",
        "padding": "24px",
    }


def _dashboard_container_style(authenticated):
    return {"display": "block" if authenticated else "none"}


def build_login_page(authenticated=False):
    return html.Div(
        id="login-container",
        style=_login_container_style(authenticated),
        children=[
            html.Div(
                style={
                    "width": "100%",
                    "maxWidth": "460px",
                    "backgroundColor": "white",
                    "borderRadius": "24px",
                    "padding": "42px",
                    "boxShadow": "0 18px 45px rgba(0,0,0,0.28)",
                    "textAlign": "center",
                },
                children=[
                    html.Img(
                        src=logo_src,
                        style={"height": "62px", "maxWidth": "100%", "marginBottom": "22px"},
                    ) if logo_src else html.H1(
                        "Keystone",
                        style={"color": "#4200A8", "marginBottom": "22px"},
                    ),
                    html.H1(
                        "Employer Database",
                        style={
                            "color": "#2E1654",
                            "fontSize": "28px",
                            "margin": "0 0 10px",
                        },
                    ),
                    html.P(
                        "Enter the access password to view the dashboard.",
                        style={
                            "color": "#6F5A8C",
                            "fontSize": "15px",
                            "margin": "0 0 26px",
                        },
                    ),
                    dcc.Input(
                        id="login-password",
                        type="password",
                        placeholder="Access password",
                        n_submit=0,
                        style={
                            "width": "100%",
                            "height": "48px",
                            "padding": "12px 14px",
                            "borderRadius": "10px",
                            "border": "1px solid #CCCCCC",
                            "fontSize": "16px",
                            "marginBottom": "14px",
                        },
                    ),
                    html.Button(
                        "Sign in",
                        id="login-submit-btn",
                        n_clicks=0,
                        style={
                            "width": "100%",
                            "height": "48px",
                            "border": "none",
                            "borderRadius": "10px",
                            "backgroundColor": "#66F2E3",
                            "color": "#2E1654",
                            "fontSize": "16px",
                            "fontWeight": "bold",
                            "cursor": "pointer",
                        },
                    ),
                    html.Div(
                        id="login-message",
                        style={
                            "color": "#B42318",
                            "fontSize": "14px",
                            "minHeight": "22px",
                            "marginTop": "14px",
                        },
                    ),
                ],
            )
        ],
    )


def serve_layout():
    authenticated = (
        has_request_context() and session.get("authenticated") is True
    )
    return html.Div(
        style={"minHeight": "100vh", "backgroundColor": "#4200A8"},
        children=[
            dcc.Store(
                id="auth-session",
                data={"authenticated": authenticated},
                storage_type="session",
            ),
            build_login_page(authenticated),
            html.Div(
                id="dashboard-container",
                style=_dashboard_container_style(authenticated),
                children=[dashboard_layout],
            ),
        ],
    )


app.layout = serve_layout


@app.callback(
    Output("auth-session", "data"),
    Output("login-message", "children"),
    Output("login-password", "value"),
    Output("login-container", "style"),
    Output("dashboard-container", "style"),
    Input("login-submit-btn", "n_clicks"),
    Input("logout-btn", "n_clicks"),
    State("login-password", "value"),
    prevent_initial_call=True,
)
def authenticate_user(n_clicks, logout_clicks, password):
    if ctx.triggered_id == "logout-btn":
        if not logout_clicks:
            raise PreventUpdate
        session.pop("authenticated", None)
        return (
            {"authenticated": False},
            "",
            "",
            _login_container_style(False),
            _dashboard_container_style(False),
        )

    if ctx.triggered_id != "login-submit-btn" or not n_clicks:
        raise PreventUpdate

    password_text = "" if password is None else str(password)
    if secrets.compare_digest(password_text, ACCESS_PASSWORD):
        session["authenticated"] = True
        return (
            {"authenticated": True},
            "",
            "",
            _login_container_style(True),
            _dashboard_container_style(True),
        )

    session.pop("authenticated", None)
    return (
        {"authenticated": False},
        "Incorrect password. Please try again.",
        "",
        _login_container_style(False),
        _dashboard_container_style(False),
    )


@app.callback(
    Output("category-filter-wrapper", "style"),
    Output("category-filter", "value"),
    Input("industry-filter", "value"),
)
def toggle_category_filter(industry):
    if industry:
        return {
            "display": "block",
            "marginTop": "8px",
            "marginLeft": "24px",
            "paddingLeft": "14px",
            "borderLeft": "3px solid #66F2E3",
        }, None
    return {"display": "none"}, None


@app.callback(
    Output("business-table", "data"),
    Output("result-count", "children"),
    Output("industry-filter", "options"),
    Output("category-filter", "options"),
    Output("suburb-filter", "options"),
    Output("accessibility-filter", "options"),
    Output("review-count-filter", "options"),
    Input("search-input", "value"),
    Input("industry-filter", "value"),
    Input("category-filter", "value"),
    Input("suburb-filter", "value"),
    Input("accessibility-filter", "value"),
    Input("review-count-filter", "value"),
    Input("favourites-only-filter", "value"),
    Input("fav-update-trigger", "data"),
    Input("auth-session", "data"),
)
def update_table(search, industry, category, suburb, accessibility, review_count, fav_only, _trig, _auth):
    fav_set = load_favourites()
    selected = {
        "search": search, "industry": industry, "category": category,
        "suburb": suburb, "accessibility": accessibility,
        "review_count": review_count,
        "favourites_only": fav_only, "fav_set": fav_set,
    }

    filtered = apply_filters(businesses, **selected)

    industry_data = apply_filters(businesses, **selected, ignore={"industry"})
    category_data = apply_filters(businesses, **selected, ignore={"category"})
    suburb_data = apply_filters(businesses, **selected, ignore={"suburb"})

    # Sort: favourites first
    filtered["_is_fav"] = filtered["Business Name"].isin(fav_set)
    filtered = filtered.sort_values(by="_is_fav", ascending=False).drop(columns=["_is_fav"])

    display_data = filtered.copy().reset_index().rename(columns={"index": "_row_idx"})

    display_data["Website"] = display_data["Website"].apply(
        lambda link: f"[🌐 Website]({link})" if str(link).strip() else ""
    )

    output_cols = TABLE_COLS + ["_row_idx"]
    return (
        display_data[output_cols].to_dict("records"),
        f"{len(display_data)} businesses found",
        make_options(industry_data["Industry"]),
        make_options(category_data["Category"]),
        make_options(suburb_data["Suburb"]),
        [{"label": f, "value": f} for f in ACCESSIBILITY_FEATURES],
        REVIEW_COUNT_OPTIONS,
    )


def _detail_field(label, value, is_link=False, icon="", link_text="Open link →"):
    label_text = f"{icon} {label}" if icon else label
    if is_link and value:
        return html.Div([
            html.Strong(f"{label_text}: ", style={"color": "#2E1654"}),
            html.A(
                link_text,
                href=value,
                target="_blank",
                style={
                    "display": "inline-block",
                    "background": "#66F2E3",
                    "color": "#2E1654",
                    "padding": "6px 14px",
                    "borderRadius": "20px",
                    "textDecoration": "none",
                    "fontWeight": "bold",
                    "fontSize": "13px",
                    "transition": "transform 0.1s, box-shadow 0.1s",
                }
            )
        ], style={"marginBottom": "10px"})
    return html.Div([
        html.Strong(f"{label_text}: ", style={"color": "#2E1654"}),
        html.Span(str(value) if value not in [None, ""] else "—", style={"color": "#333"})
    ], style={"marginBottom": "10px"})


def _category_card(title, icon, fields):
    return html.Div(
        style={
            "background": "#F8F5FF",
            "borderRadius": "12px",
            "padding": "16px",
            "marginBottom": "16px",
        },
        children=[
            html.H4(f"{icon} {title}", style={"color": "#2E1654", "marginTop": "0", "marginBottom": "12px", "fontSize": "16px"}),
            html.Div(fields),
        ],
    )


def _build_modal_content(business_name, row):
    fav_set = load_favourites()
    is_fav = business_name in fav_set
    comments_dict = load_comments()
    comments = comments_dict.get(business_name, [])

    if comments:
        comments_children = []
        for i, c in enumerate(comments):
            comments_children.append(
                html.Div([
                    html.Div([
                        html.Small(
                            datetime.fromisoformat(c["time"]).strftime("%d %b %Y %H:%M"),
                            style={"color": "#888", "fontSize": "12px"}
                        ),
                        html.Button(
                            "🗑️",
                            id={"type": "delete-comment-btn", "index": i},
                            n_clicks=0,
                            title="Delete comment",
                            style={
                                "background": "none",
                                "border": "none",
                                "cursor": "pointer",
                                "fontSize": "16px",
                                "padding": "0 4px",
                            }
                        ),
                    ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"}),
                    html.P(c["text"], style={"marginTop": "4px", "color": "#333", "whiteSpace": "pre-wrap"})
                ], style={"background": "#F8F5FF", "padding": "12px", "borderRadius": "8px", "marginBottom": "8px"})
            )
    else:
        comments_children = html.P(
            "💬 No comments yet. Be the first to add one!",
            style={"color": "#888", "fontStyle": "italic"}
        )

    # Business Contact
    email_val = row.get("Email")
    if not email_val or str(email_val).strip() == "":
        email_val = "—"

    contact_fields = [
        _detail_field("Phone", row.get("Phone"), icon="📞"),
        _detail_field("Email", email_val, icon="✉️"),
        _detail_field("Website", row.get("Website"), is_link=True, icon="🌐", link_text="🌐 Website"),
        _detail_field("Address", row.get("Address"), icon="📍"),
        _detail_field("Google Maps", row.get("Google Maps"), is_link=True, icon="🗺️", link_text="🗺️ Directions"),
    ]

    # Format review count and rating
    rc = row.get("Reviews Count")
    if pd.isna(rc) or rc == "" or rc is None:
        rc_display = "—"
    else:
        rc_display = str(int(float(rc)))

    ts = row.get("Total Score")
    if pd.isna(ts) or ts == "" or ts is None:
        ts_display = "—"
    else:
        ts_display = str(ts)

    # Business Specs
    specs_fields = [
        _detail_field("Category", row.get("Category"), icon="📂"),
        _detail_field("Industry", row.get("Industry"), icon="🏭"),
    ]
    for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        val = row.get(day, "")
        if not val or str(val).strip() == "":
            val = "—"
        specs_fields.append(_detail_field(day, val))
    specs_fields.extend([
        _detail_field("Reviews Count", rc_display, icon="💬"),
        _detail_field("Rating", ts_display, icon="⭐"),
    ])

    # Accessibility
    accessibility_fields = []
    for feature in ACCESSIBILITY_FEATURES:
        val = row.get(feature)
        display_val = "Yes" if val == True else "—"
        accessibility_fields.append(_detail_field(feature, display_val))

    return html.Div([
        html.Div([
            html.H2(
                business_name,
                style={"color": "#2E1654", "margin": "0", "fontSize": "32px", "display": "inline"}
            ),
            html.Button(
                "★" if is_fav else "☆",
                id="fav-btn",
                n_clicks=0,
                title="Remove favourite" if is_fav else "Add favourite",
                style={
                    "background": "none",
                    "border": "none",
                    "fontSize": "32px",
                    "cursor": "pointer",
                    "color": "#FFD700" if is_fav else "#CCCCCC",
                    "padding": "0 0 0 10px",
                    "lineHeight": "1",
                    "verticalAlign": "middle",
                    "fontFamily": "Arial, sans-serif",
                }
            ),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "20px", "paddingRight": "40px"}),

        _category_card("Business Contact", "📇", contact_fields),
        _category_card("Business Specs", "📋", specs_fields),
        _category_card("Accessibility", "♿", accessibility_fields),

        html.Hr(style={"border": "none", "borderTop": "1px solid #EEEEEE", "margin": "20px 0"}),

        html.H4("💬 Comments", style={"color": "#2E1654", "marginBottom": "12px"}),
        html.Div(comments_children, style={"marginBottom": "16px"}),

        dcc.Textarea(
            id="comment-input",
            placeholder="Write a note about this business...",
            style={
                "width": "100%", "height": "80px", "padding": "12px",
                "borderRadius": "8px", "border": "1px solid #CCCCCC",
                "fontFamily": "Arial, sans-serif", "fontSize": "14px",
                "marginBottom": "10px", "resize": "vertical"
            }
        ),
        html.Button(
            "➕ Add comment",
            id="add-comment-btn",
            n_clicks=0,
            style={
                "background": "#66F2E3", "color": "#2E1654", "border": "none",
                "padding": "10px 20px", "borderRadius": "8px",
                "fontWeight": "bold", "cursor": "pointer", "fontSize": "14px"
            }
        ),
    ])



@app.callback(
    Output("modal-overlay", "style"),
    Output("modal-content", "children"),
    Output("current-business-store", "data"),
    Output("business-table", "active_cell"),
    Input("business-table", "active_cell"),
    Input("fav-update-trigger", "data"),
    Input("comment-update-trigger", "data"),
    Input("close-modal-btn", "n_clicks"),
    State("business-table", "data"),
    State("current-business-store", "data"),
    prevent_initial_call=True,
)
def update_modal(active_cell, _fav, _com, close_clicks, table_data, current_business):
    triggered = ctx.triggered_id

    if triggered == "close-modal-btn" and close_clicks:
        return {"display": "none"}, html.Div(), None, None

    if triggered in ("fav-update-trigger", "comment-update-trigger"):
        if not current_business:
            raise PreventUpdate
        business_name = current_business
        match = businesses[businesses["Business Name"] == business_name]
        if match.empty:
            raise PreventUpdate
        row = match.iloc[0].to_dict()
        detail = _build_modal_content(business_name, row)
        return {"display": "flex"}, detail, business_name, no_update

    if not active_cell or not table_data:
        raise PreventUpdate

    row_idx = active_cell.get("row")
    if row_idx is None or row_idx >= len(table_data):
        raise PreventUpdate

    row_data = table_data[row_idx]
    business_name = row_data.get("Business Name")
    if not business_name:
        raise PreventUpdate

    orig_idx = row_data.get("_row_idx")
    try:
        row = businesses.loc[orig_idx].to_dict()
    except Exception:
        raise PreventUpdate

    detail = _build_modal_content(business_name, row)
    return {"display": "flex"}, detail, business_name, no_update


@app.callback(
    Output("fav-update-trigger", "data"),
    Input("fav-btn", "n_clicks"),
    State("current-business-store", "data"),
    prevent_initial_call=True,
)
def toggle_favourite(n_clicks, business_name):
    if not n_clicks or not business_name:
        raise PreventUpdate

    fav_set = load_favourites()
    if business_name in fav_set:
        fav_set.remove(business_name)
    else:
        fav_set.add(business_name)
    save_favourites(fav_set)

    return n_clicks


@app.callback(
    Output("comment-update-trigger", "data"),
    Output("comment-input", "value"),
    Input("add-comment-btn", "n_clicks"),
    Input({"type": "delete-comment-btn", "index": ALL}, "n_clicks"),
    State("current-business-store", "data"),
    State("comment-input", "value"),
    prevent_initial_call=True,
)
def manage_comments(add_clicks, delete_clicks_list, business_name, text):
    if not business_name:
        raise PreventUpdate

    triggered_id = ctx.triggered_id

    # Add comment
    if triggered_id == "add-comment-btn":
        if not add_clicks or not text or not text.strip():
            raise PreventUpdate

        comments_dict = load_comments()
        if business_name not in comments_dict:
            comments_dict[business_name] = []

        comments_dict[business_name].append({
            "time": datetime.now().isoformat(),
            "text": text.strip(),
        })
        save_comments(comments_dict)

        return add_clicks, ""

    # Delete comment
    elif isinstance(triggered_id, dict) and triggered_id.get("type") == "delete-comment-btn":
        comment_idx = triggered_id["index"]

        comments_dict = load_comments()
        if business_name not in comments_dict:
            raise PreventUpdate

        comments = comments_dict[business_name]
        if 0 <= comment_idx < len(comments):
            comments.pop(comment_idx)
            if not comments:
                del comments_dict[business_name]
            save_comments(comments_dict)
            return datetime.now().timestamp(), text

    raise PreventUpdate


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=False)
