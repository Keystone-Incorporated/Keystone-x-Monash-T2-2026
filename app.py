from dash import Dash, html, dcc, dash_table, Input, Output
import pandas as pd

app = Dash(__name__)

# Temporary sample data
businesses = pd.DataFrame(
    [
        {
            "Business Name": "Bright Path Services",
            "Industry": "Community Services",
            "Location": "Melbourne",
            "Business Size": "Small",
            "Skills": "Communication, Administration",
            "Email": "contact@brightpath.com",
        },
        {
            "Business Name": "TechBridge Australia",
            "Industry": "Technology",
            "Location": "Clayton",
            "Business Size": "Medium",
            "Skills": "Python, Data Analysis",
            "Email": "hello@techbridge.com",
        },
        {
            "Business Name": "Green Future Co.",
            "Industry": "Sustainability",
            "Location": "Abbotsford",
            "Business Size": "Large",
            "Skills": "Research, Reporting",
            "Email": "info@greenfuture.com",
        },
    ]
)

app.layout = html.Div(
    style={
        "backgroundColor": "#4200a8",
        "minHeight": "100vh",
        "fontFamily": "Arial, sans-serif",
        "padding": "0",
        "margin": "0",
    },
    children=[
        # Header
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
                        "color": "#66f2e3",
                        "margin": "0",
                        "fontSize": "32px",
                    },
                ),
                html.Div(
                    "Business Search Dashboard",
                    style={
                        "color": "white",
                        "fontSize": "16px",
                    },
                ),
            ],
        ),

        # Main content
        html.Div(
            style={
                "maxWidth": "1250px",
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
                    "Search and filter businesses by industry, location, size and skills.",
                    style={
                        "color": "#d9ccff",
                        "fontSize": "18px",
                        "marginBottom": "30px",
                    },
                ),

                # Filter card
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
                            style={
                                "fontWeight": "bold",
                                "color": "#2e1654",
                            },
                        ),
                        dcc.Input(
                            id="search-input",
                            type="text",
                            placeholder="Search by business name or skill...",
                            style={
                                "width": "100%",
                                "padding": "14px",
                                "marginTop": "8px",
                                "marginBottom": "20px",
                                "borderRadius": "10px",
                                "border": "1px solid #cccccc",
                                "fontSize": "16px",
                                "boxSizing": "border-box",
                            },
                        ),

                        html.Div(
                            style={
                                "display": "grid",
                                "gridTemplateColumns": "repeat(4, 1fr)",
                                "gap": "16px",
                            },
                            children=[
                                dcc.Dropdown(
                                    id="industry-filter",
                                    options=[
                                        {"label": value, "value": value}
                                        for value in sorted(
                                            businesses["Industry"].unique()
                                        )
                                    ],
                                    placeholder="Industry",
                                    clearable=True,
                                ),
                                dcc.Dropdown(
                                    id="location-filter",
                                    options=[
                                        {"label": value, "value": value}
                                        for value in sorted(
                                            businesses["Location"].unique()
                                        )
                                    ],
                                    placeholder="Location",
                                    clearable=True,
                                ),
                                dcc.Dropdown(
                                    id="size-filter",
                                    options=[
                                        {"label": value, "value": value}
                                        for value in sorted(
                                            businesses["Business Size"].unique()
                                        )
                                    ],
                                    placeholder="Business size",
                                    clearable=True,
                                ),
                                dcc.Dropdown(
                                    id="skills-filter",
                                    options=[
                                        {"label": skill, "value": skill}
                                        for skill in [
                                            "Administration",
                                            "Communication",
                                            "Data Analysis",
                                            "Python",
                                            "Reporting",
                                            "Research",
                                        ]
                                    ],
                                    placeholder="Skills",
                                    clearable=True,
                                ),
                            ],
                        ),
                    ],
                ),

                # Results section
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
                                "color": "#2e1654",
                                "fontSize": "24px",
                                "marginTop": "0",
                            },
                        ),
                        html.Div(
                            id="result-count",
                            style={
                                "color": "#6f5a8c",
                                "marginBottom": "15px",
                            },
                        ),
                        dash_table.DataTable(
                            id="business-table",
                            columns=[
                                {"name": col, "id": col}
                                for col in businesses.columns
                            ],
                            data=businesses.to_dict("records"),
                            page_size=10,
                            style_table={
                                "overflowX": "auto",
                                "borderRadius": "12px",
                            },
                            style_header={
                                "backgroundColor": "#66f2e3",
                                "color": "#2e1654",
                                "fontWeight": "bold",
                                "border": "none",
                                "padding": "12px",
                            },
                            style_cell={
                                "textAlign": "left",
                                "padding": "12px",
                                "border": "1px solid #eeeeee",
                                "fontFamily": "Arial, sans-serif",
                            },
                            style_data_conditional=[
                                {
                                    "if": {"row_index": "odd"},
                                    "backgroundColor": "#f8f5ff",
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
    Input("search-input", "value"),
    Input("industry-filter", "value"),
    Input("location-filter", "value"),
    Input("size-filter", "value"),
    Input("skills-filter", "value"),
)
def filter_businesses(search, industry, location, size, skill):
    filtered = businesses.copy()

    if search:
        search = search.lower()
        filtered = filtered[
            filtered["Business Name"].str.lower().str.contains(search)
            | filtered["Skills"].str.lower().str.contains(search)
        ]

    if industry:
        filtered = filtered[filtered["Industry"] == industry]

    if location:
        filtered = filtered[filtered["Location"] == location]

    if size:
        filtered = filtered[filtered["Business Size"] == size]

    if skill:
        filtered = filtered[
            filtered["Skills"].str.contains(skill, case=False, na=False)
        ]

    return (
        filtered.to_dict("records"),
        f"{len(filtered)} businesses found",
    )


if __name__ == "__main__":
    app.run(debug=True)