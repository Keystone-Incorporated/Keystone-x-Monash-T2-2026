from pathlib import Path
import json
import base64
from datetime import datetime
import pandas as pd
from dash import Dash, Input, Output, State, dash_table, dcc, html, ctx, ALL
from dash.exceptions import PreventUpdate


# ── Paths ────────────────────────────────────────────────────────────────────
DATA_FILE = Path(__file__).with_name("Fake_Dataset_For_Testing.csv")
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

if "Favourite" not in businesses.columns:
    businesses["Favourite"] = "No"

required_columns = [
    "Business Name", "Phone", "Email", "Website", "Address",
    "Google Maps", "Size", "Industry", "Skills", "Interests", "Wheelchair",
]
missing = [c for c in required_columns if c not in businesses.columns]
if missing:
    raise ValueError("Missing columns: " + ", ".join(missing))


# ── Helpers ──────────────────────────────────────────────────────────────────
def split_items(value):
    return [item.strip() for item in str(value).split(",") if item.strip()]


def make_options(values):
    clean = sorted({str(v).strip() for v in values if str(v).strip()})
    return [{"label": v, "value": v} for v in clean]


def make_multi_value_options(series):
    items = set()
    for value in series:
        items.update(split_items(value))
    return make_options(items)


def apply_filters(
    data,
    search=None,
    industry=None,
    size=None,
    skill=None,
    interest=None,
    wheelchair=None,
    address=None,
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
    if size and "size" not in ignore:
        filtered = filtered[filtered["Size"] == size]
    if skill and "skill" not in ignore:
        filtered = filtered[
            filtered["Skills"].astype(str).str.contains(skill, case=False, na=False, regex=False)
        ]
    if interest and "interest" not in ignore:
        filtered = filtered[
            filtered["Interests"].astype(str).str.contains(interest, case=False, na=False, regex=False)
        ]
    if wheelchair and "wheelchair" not in ignore:
        filtered = filtered[
            filtered["Wheelchair"].astype(str).str.casefold() == str(wheelchair).casefold()
        ]
    if address and "address" not in ignore:
        filtered = filtered[filtered["Address"] == address]
    if favourites_only == "yes" and "favourites" not in ignore and fav_set is not None:
        filtered = filtered[filtered["Business Name"].isin(fav_set)]
    return filtered


# Compact columns shown in the main dashboard table
TABLE_COLS = ["Business Name", "Phone", "Website", "Address", "Industry", "Favourite"]

# ── App ──────────────────────────────────────────────────────────────────────
app = Dash(__name__)
app.title = "Keystone Employer Database"

app.index_string = """
<!DOCTYPE html>
<html>
    <head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
    <style>
        html, body, #react-entry-point { margin: 0; min-height: 100%; background: #4200A8; }
        * { box-sizing: border-box; }
        /* Make every link inside the data table look like a pill button */
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
    </style></head>
    <body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body>
</html>
"""

app.layout = html.Div(
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
                html.A("🌐 keystone.org.au", href="https://www.keystone.org.au/", target="_blank", style={"color": "white", "fontSize": "16px", "fontWeight": "bold", "textDecoration": "none"}),
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
                            style={"width": "100%", "padding": "14px", "marginTop": "8px", "marginBottom": "20px", "borderRadius": "10px", "border": "1px solid #CCCCCC", "fontSize": "16px"},
                        ),
                        html.Div(
                            style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(190px, 1fr))", "gap": "16px"},
                            children=[
                                dcc.Dropdown(id="industry-filter", placeholder="🏭 Industry", clearable=True),
                                dcc.Dropdown(id="size-filter", placeholder="📏 Business size", clearable=True),
                                dcc.Dropdown(id="skills-filter", placeholder="🛠️ Skills", clearable=True),
                                dcc.Dropdown(id="interests-filter", placeholder="💡 Interests", clearable=True),
                                dcc.Dropdown(id="wheelchair-filter", placeholder="♿ Wheelchair accessibility", clearable=True),
                                dcc.Dropdown(id="address-filter", placeholder="📍 Address / location", clearable=True),
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
                            row_selectable="single",
                            selected_rows=[],
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
                        html.Button(
                            "✕ Clear Selection",
                            id="clear-selection-btn",
                            n_clicks=0,
                            style={
                                "marginTop": "16px",
                                "background": "#FF6B6B",
                                "color": "white",
                                "border": "none",
                                "padding": "8px 18px",
                                "borderRadius": "8px",
                                "fontWeight": "bold",
                                "cursor": "pointer",
                                "fontSize": "13px",
                            }
                        ),
                    ],
                ),

                # ── Detail Panel ─────────────────────────────────────────────
                html.Div(
                    id="detail-panel",
                    style={"backgroundColor": "white", "borderRadius": "20px", "padding": "28px", "boxShadow": "0 12px 30px rgba(0,0,0,0.20)", "marginTop": "30px"},
                    children=[
                        html.P("👆 Click a business in the table above to view details and comments.", style={"color": "#6F5A8C", "textAlign": "center", "padding": "20px"})
                    ],
                ),
            ],
        ),
    ],
)

# ── Callbacks ────────────────────────────────────────────────────────────────

@app.callback(
    Output("business-table", "data"),
    Output("result-count", "children"),
    Output("industry-filter", "options"),
    Output("size-filter", "options"),
    Output("skills-filter", "options"),
    Output("interests-filter", "options"),
    Output("wheelchair-filter", "options"),
    Output("address-filter", "options"),
    Input("search-input", "value"),
    Input("industry-filter", "value"),
    Input("size-filter", "value"),
    Input("skills-filter", "value"),
    Input("interests-filter", "value"),
    Input("wheelchair-filter", "value"),
    Input("address-filter", "value"),
    Input("favourites-only-filter", "value"),
    Input("fav-update-trigger", "data"),
)
def update_table(search, industry, size, skill, interest, wheelchair, address, fav_only, _trig):
    fav_set = load_favourites()
    selected = {
        "search": search, "industry": industry, "size": size,
        "skill": skill, "interest": interest, "wheelchair": wheelchair,
        "address": address, "favourites_only": fav_only, "fav_set": fav_set,
    }

    filtered = apply_filters(businesses, **selected)

    industry_data = apply_filters(businesses, **selected, ignore={"industry"})
    size_data = apply_filters(businesses, **selected, ignore={"size"})
    skill_data = apply_filters(businesses, **selected, ignore={"skill"})
    interest_data = apply_filters(businesses, **selected, ignore={"interest"})
    wheelchair_data = apply_filters(businesses, **selected, ignore={"wheelchair"})
    address_data = apply_filters(businesses, **selected, ignore={"address"})

    # Sort: favourites first
    filtered["_is_fav"] = filtered["Business Name"].isin(fav_set)
    filtered = filtered.sort_values(by="_is_fav", ascending=False).drop(columns=["_is_fav"])

    # Preserve original index so we can look up the exact row later
    display_data = filtered.copy().reset_index().rename(columns={"index": "_row_idx"})

    display_data["Website"] = display_data["Website"].apply(
        lambda link: f"[🌐 Website]({link})" if str(link).strip() else ""
    )
    display_data["Favourite"] = display_data["Business Name"].apply(
        lambda name: "⭐" if name in fav_set else "☆"
    )

    # Only return columns needed for display + hidden index
    output_cols = TABLE_COLS + ["_row_idx"]
    return (
        display_data[output_cols].to_dict("records"),
        f"{len(display_data)} businesses found",
        make_options(industry_data["Industry"]),
        make_options(size_data["Size"]),
        make_multi_value_options(skill_data["Skills"]),
        make_multi_value_options(interest_data["Interests"]),
        make_options(wheelchair_data["Wheelchair"]),
        make_options(address_data["Address"]),
    )


@app.callback(
    Output("business-table", "selected_rows"),
    Input("clear-selection-btn", "n_clicks"),
    prevent_initial_call=True,
)
def clear_selection(n_clicks):
    return []


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
        html.Span(str(value) if value else "—", style={"color": "#333"})
    ], style={"marginBottom": "10px"})


@app.callback(
    Output("detail-panel", "children"),
    Output("current-business-store", "data"),
    Input("business-table", "selected_rows"),
    Input("fav-update-trigger", "data"),
    Input("comment-update-trigger", "data"),
    State("business-table", "data"),
)
def update_detail_panel(selected_rows, _fav, _com, table_data):
    if not selected_rows or not table_data:
        return html.P(
            "👆 Click a business in the table above to view details and comments.",
            style={"color": "#6F5A8C", "textAlign": "center", "padding": "20px"}
        ), None

    row_data = table_data[selected_rows[0]]
    business_name = row_data.get("Business Name")
    if not business_name:
        return html.P("No business selected.", style={"color": "#6F5A8C", "textAlign": "center"}), None

    # Use the hidden _row_idx to get the EXACT original row (handles duplicates)
    row_idx = row_data.get("_row_idx")
    try:
        row = businesses.loc[row_idx].to_dict()
    except Exception:
        return html.P("Business not found.", style={"color": "#6F5A8C", "textAlign": "center"}), None

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

    detail = html.Div([
        html.Div([
            html.H2(business_name, style={"color": "#2E1654", "margin": "0", "fontSize": "28px"}),
            html.Button(
                "⭐ Remove favourite" if is_fav else "☆ Add to favourites",
                id="fav-btn",
                n_clicks=0,
                style={
                    "background": "#66F2E3" if is_fav else "#4200A8",
                    "color": "#2E1654" if is_fav else "white",
                    "border": "none",
                    "padding": "10px 20px",
                    "borderRadius": "8px",
                    "fontWeight": "bold",
                    "cursor": "pointer",
                    "fontSize": "14px",
                }
            ),
        ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "20px"}),

        html.Hr(style={"border": "none", "borderTop": "1px solid #EEEEEE", "margin": "20px 0"}),

        html.Div([
            _detail_field("Phone", row.get("Phone"), icon="📞"),
            _detail_field("Email", row.get("Email"), icon="✉️"),
            _detail_field("Website", row.get("Website"), is_link=True, icon="🌐", link_text="🌐 Website"),
            _detail_field("Address", row.get("Address"), icon="📍"),
            _detail_field("Google Maps", row.get("Google Maps"), is_link=True, icon="🗺️", link_text="🗺️ Directions"),
            _detail_field("Size", row.get("Size"), icon="📏"),
            _detail_field("Industry", row.get("Industry"), icon="🏭"),
            _detail_field("Skills", row.get("Skills"), icon="🛠️"),
            _detail_field("Interests", row.get("Interests"), icon="💡"),
            _detail_field("Wheelchair", row.get("Wheelchair"), icon="♿"),
        ], style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(280px, 1fr))", "gap": "12px"}),

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

    return detail, business_name


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

    # ── Add comment ──────────────────────────────────────────────────────
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

    # ── Delete comment ───────────────────────────────────────────────────
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