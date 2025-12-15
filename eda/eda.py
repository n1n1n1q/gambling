import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import polars as pl
    import plotly.express as px

    from pathlib import Path
    return Path, pl, px


@app.cell
def _(Path, mo):
    results_path = Path.cwd() / "output"

    dir_to_name_map = {
        f"{full_path.parent.name}/{full_path.name}": full_path for full_path in results_path.rglob("*.parquet")
    }

    scenario_data_path = mo.ui.dropdown(options=dir_to_name_map)
    scenario_data_path
    return (scenario_data_path,)


@app.cell
def _(pl, scenario_data_path):
    chosen_scenario = pl.read_parquet(scenario_data_path.value)
    return (chosen_scenario,)


@app.cell
def _(chosen_scenario, mo):
    mo.ui.dataframe(chosen_scenario)
    return


@app.cell
def _(mo, pl, px):
    tick_col = "tick"


    def make_line(df: pl.DataFrame, y_cols: list[str], title: str, y_title: str):
        df_sorted = df.sort(tick_col)
        plot_df = df_sorted.select([tick_col] + y_cols).unpivot(index=tick_col, variable_name="metric", value_name="value")
        fig = px.line(plot_df, x=tick_col, y="value", color="metric", markers=True, title=title)
        fig.update_layout(xaxis_title="tick", yaxis_title=y_title)
        return mo.ui.plotly(fig)
    return (make_line,)


@app.cell
def _(chosen_scenario, make_line, mo):
    cash_box_plot = make_line(chosen_scenario, ["cash_box"], "Cash box over tick", "cash_box")
    n_components_plot = make_line(chosen_scenario, ["n_components"], "Number of components over tick", "n_components")
    ndegree_plot = make_line(
        chosen_scenario,
        ["min_ndegree", "avg_ndegree", "max_ndegree", "cen_ndegree"],
        "Node degree stats over tick",
        "ndegree",
    )
    path_length_plot = make_line(
        chosen_scenario, ["average_path_length"], "Average path length over tick", "average_path_length"
    )
    nbetweenness_plot = make_line(
        chosen_scenario,
        ["min_nbetweenness", "avg_nbetweenness", "max_nbetweenness"],
        "Betweenness stats over tick",
        "nbetweenness",
    )
    mo.vstack([cash_box_plot, n_components_plot, ndegree_plot, path_length_plot, nbetweenness_plot])
    return


@app.cell
def _():
    import marimo as mo
    return (mo,)


if __name__ == "__main__":
    app.run()
