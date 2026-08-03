from pathlib import Path

import pandas as pd
from dash import Dash, Input, Output, dash_table, dcc, html


DATA_FILE = Path(__file__).with_name("Fake_Dataset_For_Testing.csv")

# Read the CSV stored beside app.py.
businesses = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
businesses.columns = businesses.columns.str.strip()
businesses = businesses.replace({"(blank)": "", "blank": ""}).fillna("")

required_columns = [
    "Business Name",
    "Phone",
    "Email",
    "Website",
    "Address",
    "Google Maps",
    "Size",
    "Industry",
    "Skills",
    "Interests",
    "Wheelchair",
]

missing_columns = [column for column in required_columns if column not in businesses.columns]
if missing_columns:
    raise ValueError(
        "The CSV is missing these columns: " + ", ".join(missing_columns)
    )


def split_items(value):
    """Split comma-separated values such as Skills and Interests."""
    return [item.strip() for item in str(value).split(",") if item.strip()]


def make_options(values):
    """Create sorted Dash dropdown options from non-empty values."""
    clean_values = sorted({str(value).strip() for value in values if str(value).strip()})
    return [{"label": value, "value": value} for value in clean_values]


def make_multi_value_options(series):
    """Create dropdown options from comma-separated cells."""
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
    ignore=None,
):
    """
    Filter the dataset.

    `ignore` is used when generating a dropdown's available options so that
    the dropdown does not filter its own choices.
    """
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
            filtered["Skills"]
            .astype(str)
            .str.contains(skill, case=False, na=False, regex=False)
        ]

    if interest and "interest" not in ignore:
        filtered = filtered[
            filtered["Interests"]
            .astype(str)
            .str.contains(interest, case=False, na=False, regex=False)
        ]

    if wheelchair and "wheelchair" not in ignore:
        filtered = filtered[
            filtered["Wheelchair"].astype(str).str.casefold()
            == str(wheelchair).casefold()
        ]

    if address and "address" not in ignore:
        filtered = filtered[filtered["Address"] == address]

    return filtered


app = Dash(__name__)
app.title = "Keystone Employer Database"

# Remove the browser's default white margin and keep the page purple.
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            html, body, #react-entry-point {
                margin: 0;
                min-height: 100%;
                background: #4200A8;
            }
            * {
                box-sizing: border-box;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

app.layout = html.Div(
    style={
        "backgroundColor": "#4200A8",
        "minHeight": "100vh",
        "fontFamily": "Arial, sans-serif",
        "margin": "0",
        "paddingBottom": "70px",
    },
    children=[
        html.Div(
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "padding": "25px 45px",
                "borderBottom": "1px solid rgba(255,255,255,0.15)",
            },
            children=[
                html.H1(
                    "Keystone Employer Database",
                    style={
                        "color": "#66F2E3",
                        "margin": "0",
                        "fontSize": "32px",
                    },
                ),
                html.Div(
                    "Business Search Dashboard",
                    style={"color": "white", "fontSize": "16px"},
                ),
            ],
        ),
        html.Div(
            style={
                "maxWidth": "1500px",
                "margin": "0 auto",
                "padding": "45px 30px",
            },
            children=[
                html.H2(
                    "Find the right businesses and opportunities",
                    style={
                        "color": "white",
                        "fontSize": "36px",
                        "marginBottom": "10px",
                    },
                ),
                html.P(
                    "Search by business name and filter the available results.",
                    style={
                        "color": "#D9CCFF",
                        "fontSize": "18px",
                        "marginBottom": "30px",
                    },
                ),
                html.Div(
                    style={
                        "backgroundColor": "white",
                        "borderRadius": "20px",
                        "padding": "28px",
                        "boxShadow": "0 12px 30px rgba(0,0,0,0.20)",
                        "marginBottom": "30px",
                    },
                    children=[
                        html.Label(
                            "Search businesses",
                            style={"fontWeight": "bold", "color": "#2E1654"},
                        ),
                        dcc.Input(
                            id="search-input",
                            type="text",
                            placeholder="Search by business name...",
                            debounce=True,
                            style={
                                "width": "100%",
                                "padding": "14px",
                                "marginTop": "8px",
                                "marginBottom": "20px",
                                "borderRadius": "10px",
                                "border": "1px solid #CCCCCC",
                                "fontSize": "16px",
                            },
                        ),
                        html.Div(
                            style={
                                "display": "grid",
                                "gridTemplateColumns": (
                                    "repeat(auto-fit, minmax(190px, 1fr))"
                                ),
                                "gap": "16px",
                            },
                            children=[
                                dcc.Dropdown(
                                    id="industry-filter",
                                    placeholder="Industry",
                                    clearable=True,
                                ),
                                dcc.Dropdown(
                                    id="size-filter",
                                    placeholder="Business size",
                                    clearable=True,
                                ),
                                dcc.Dropdown(
                                    id="skills-filter",
                                    placeholder="Skills",
                                    clearable=True,
                                ),
                                dcc.Dropdown(
                                    id="interests-filter",
                                    placeholder="Interests",
                                    clearable=True,
                                ),
                                dcc.Dropdown(
                                    id="wheelchair-filter",
                                    placeholder="Wheelchair accessibility",
                                    clearable=True,
                                ),
                                dcc.Dropdown(
                                    id="address-filter",
                                    placeholder="Address / location",
                                    clearable=True,
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    style={
                        "backgroundColor": "white",
                        "borderRadius": "20px",
                        "padding": "28px",
                        "boxShadow": "0 12px 30px rgba(0,0,0,0.20)",
                    },
                    children=[
                        html.H3(
                            "Business results",
                            style={
                                "color": "#2E1654",
                                "fontSize": "24px",
                                "marginTop": "0",
                            },
                        ),
                        html.Div(
                            id="result-count",
                            style={"color": "#6F5A8C", "marginBottom": "15px"},
                        ),
                        dash_table.DataTable(
                            id="business-table",
                            columns=[
                                {
                                    "name": column,
                                    "id": column,
                                    "presentation": (
                                        "markdown"
                                        if column in {"Website", "Google Maps"}
                                        else "input"
                                    ),
                                }
                                for column in businesses.columns
                            ],
                            page_size=10,
                            sort_action="native",
                            markdown_options={"link_target": "_blank"},
                            style_table={
                                "overflowX": "auto",
                                "borderRadius": "12px",
                            },
                            style_header={
                                "backgroundColor": "#66F2E3",
                                "color": "#2E1654",
                                "fontWeight": "bold",
                                "border": "none",
                                "padding": "12px",
                            },
                            style_cell={
                                "textAlign": "left",
                                "padding": "12px",
                                "border": "1px solid #EEEEEE",
                                "fontFamily": "Arial, sans-serif",
                                "minWidth": "125px",
                                "maxWidth": "270px",
                                "whiteSpace": "normal",
                            },
                            style_data_conditional=[
                                {
                                    "if": {"row_index": "odd"},
                                    "backgroundColor": "#F8F5FF",
                                }
                            ],
                        ),
                    ],
                ),
            ],
        ),
    ],
)


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
)
def update_dashboard(
    search,
    industry,
    size,
    skill,
    interest,
    wheelchair,
    address,
):
    selected = {
        "search": search,
        "industry": industry,
        "size": size,
        "skill": skill,
        "interest": interest,
        "wheelchair": wheelchair,
        "address": address,
    }

    # Final table: apply every currently selected filter.
    filtered = apply_filters(businesses, **selected)

    # Cascading dropdowns: each dropdown is based on all the other filters.
    industry_data = apply_filters(
        businesses, **selected, ignore={"industry"}
    )
    size_data = apply_filters(
        businesses, **selected, ignore={"size"}
    )
    skill_data = apply_filters(
        businesses, **selected, ignore={"skill"}
    )
    interest_data = apply_filters(
        businesses, **selected, ignore={"interest"}
    )
    wheelchair_data = apply_filters(
        businesses, **selected, ignore={"wheelchair"}
    )
    address_data = apply_filters(
        businesses, **selected, ignore={"address"}
    )

    display_data = filtered.copy()

    display_data["Website"] = display_data["Website"].apply(
        lambda link: f"[Open website]({link})" if str(link).strip() else ""
    )
    display_data["Google Maps"] = display_data["Google Maps"].apply(
        lambda link: f"[Open map]({link})" if str(link).strip() else ""
    )

    return (
        display_data.to_dict("records"),
        f"{len(display_data)} businesses found",
        make_options(industry_data["Industry"]),
        make_options(size_data["Size"]),
        make_multi_value_options(skill_data["Skills"]),
        make_multi_value_options(interest_data["Interests"]),
        make_options(wheelchair_data["Wheelchair"]),
        make_options(address_data["Address"]),
    )


if __name__ == "__main__":
    app.run(debug=True)