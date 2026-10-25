"""Plotly figures with a transparent dark glass theme."""
import plotly.express as px

from services.statuses import STATUS_ORDER

PALETTE = ["#8b6cff", "#22d3ee", "#b6ff5c", "#ff6bd6", "#ffd37a", "#4f8bff", "#7dffb0", "#ff8aa0"]


def _style(fig, height=320):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, sans-serif", color="#cfd5ff"), height=height,
                      margin=dict(l=8, r=8, t=24, b=8), colorway=PALETTE, legend_title_text="")
    fig.update_xaxes(gridcolor="rgba(255,255,255,.07)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,.07)", zeroline=False)
    return fig


def status_bar(counts_df):
    fig = px.bar(counts_df, x="status", y="count", text="count", color="status",
                 category_orders={"status": [s.label for s in STATUS_ORDER]})
    fig.update_traces(marker_line_width=0, textposition="outside")
    fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Applications")
    fig.update_yaxes(dtick=1)
    return _style(fig)


def status_donut(counts_df):
    data = counts_df[counts_df["count"] > 0]
    fig = px.pie(data, names="status", values="count", hole=.62)
    fig.update_traces(textinfo="value", marker=dict(line=dict(color="#060914", width=2)))
    return _style(fig)


def drives_stacked(matrix_df):
    data = matrix_df.drop(columns=["Total"]).reset_index().melt(id_vars="drive", var_name="Stage", value_name="Applications")
    fig = px.bar(data, y="drive", x="Applications", color="Stage", orientation="h",
                 category_orders={"Stage": [s.label for s in STATUS_ORDER]})
    fig.update_layout(yaxis_title=None)
    return _style(fig, height=max(280, 54 * len(matrix_df) + 80))


def trend_line(df):
    fig = px.area(df, x="date", y="applications")
    fig.update_traces(line=dict(color="#22d3ee", width=3), fillcolor="rgba(34,211,238,.18)")
    fig.update_layout(xaxis_title=None, yaxis_title="Cumulative applications")
    return _style(fig)


def package_bar(df):
    fig = px.bar(df, x="drive", y="package", text="package", color="package", color_continuous_scale=["#4f8bff", "#8b6cff", "#ff6bd6"])
    fig.update_layout(xaxis_title=None, yaxis_title="Package (LPA)", coloraxis_showscale=False)
    fig.update_traces(texttemplate="%{text:g}", textposition="outside", marker_line_width=0)
    return _style(fig)
