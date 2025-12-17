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
    results_path = Path.cwd() / "outputs_100orgs"

    dir_to_name_map = {
        f"{full_path.parent.name}/{full_path.name}": full_path for full_path in results_path.rglob("*.parquet")
    }

    scenario_data_path = mo.ui.dropdown(options=dir_to_name_map)
    scenario_data_path
    return results_path, scenario_data_path


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
def _(mo, pl, results_path):
    for file_path in mo.status.progress_bar(list(results_path.rglob("*.parquet"))):
        tmp_data = pl.read_parquet(file_path)

        arrest_perc = int(file_path.parent.name.split("_")[1])

        tmp_data = tmp_data.with_columns(pl.lit(arrest_perc).alias("ArrestPerc"))
        tmp_data.write_parquet(file_path)
    return


@app.cell
def _(pl, results_path):
    full_data = (
        pl.scan_parquet(list(results_path.rglob("*.parquet")))
        .with_columns(pl.col("tick").floordiv(365).alias("Year"))
        .with_columns(pl.col("tick").mod(30).eq(0).alias("EndOfMonth"), pl.col("tick").mod(365).eq(0).alias("EndOfYear"))
    )
    return (full_data,)


@app.cell
def _(full_data, pl):
    data_perc_grouped = (
        full_data.filter(pl.col("EndOfYear").eq(1))
        .group_by("ArrestPerc", "Year", "run_index")
        .agg(pl.col("n_active_organizations").max().name.suffix("_max_end"))
        .collect()
        .group_by("ArrestPerc", "Year")
        .agg(pl.col("n_active_organizations_max_end").sum().name.suffix("_sum"))
        .sort(by="Year")
        .with_columns(pl.format("Year {}", pl.col("Year")))
        .pivot(index="ArrestPerc", on="Year", values="n_active_organizations_max_end_sum")
        .with_columns(pl.lit(30).alias("Year 0"))
    )
    return (data_perc_grouped,)


@app.cell
def _(data_perc_grouped, mo):
    mo.ui.dataframe(data_perc_grouped)
    return


@app.cell
def _(full_data, mo, pl):
    data_perc_grouped_monthly = (
        full_data.filter(pl.col("EndOfMonth").eq(1))
        .group_by("ArrestPerc", "tick")
        .agg(pl.col("n_active_organizations").sum().name.suffix("_max_end"))
        .collect()
    ).sort(by=["tick","ArrestPerc"])

    mo.ui.dataframe(data_perc_grouped_monthly)
    return (data_perc_grouped_monthly,)


@app.cell
def _(data_perc_grouped_monthly, pl, px):
    fig = px.line(
        data_perc_grouped_monthly.with_columns(pl.col("ArrestPerc").cast(pl.String)), 
        x="tick", 
        y="n_active_organizations_max_end", 
        color="ArrestPerc",
        markers=True,
        title="Monthly Active Organizations over Tick by Arrest Percentage",
        labels={
            "tick": "Tick",
            "n_active_organizations_max_end": "Num Active Organizations",
            "ArrestPerc": "Arrest %"
        }
    )

    # Show the plot
    fig.show()
    return


@app.cell
def _(full_data, pl):
    data_num_members = full_data.filter(pl.col("EndOfMonth").eq(1)).group_by("ArrestPerc", "tick").agg(pl.col("n_total_members").mean(), pl.col("EndOfYear").get(0)).collect().sort(by=["tick", "ArrestPerc"])

    return (data_num_members,)


@app.cell
def _(data_num_members, px):
    fig_members = px.line(
        data_num_members, 
        x="tick", 
        y="n_total_members", 
        facet_col="ArrestPerc",      # Creates a separate plot for each ArrestPerc
        facet_col_wrap=3,            # Arranges plots in a grid (3 columns wide)
        markers=True,                # Adds markers to the lines
        title="Total Members over Ticks by Arrest Percentage",
        labels={
            "tick": "Tick", 
            "n_total_members": "Total Members",
            "ArrestPerc": "Arrest %"
        }
    )

    fig_members.update_layout(height=1000)
    fig_members.show()
    return


@app.cell
def _(full_data, pl):
    data_revenue = full_data.filter(pl.col("EndOfMonth").eq(1)).group_by("ArrestPerc", "tick").agg(pl.col("revenues").mean(), pl.col("EndOfYear")).collect().sort(by=["tick", "ArrestPerc"])
    return (data_revenue,)


@app.cell
def _(data_revenue, px):
    fig_revenues = px.line(
        data_revenue,
        x="tick", 
        y="revenues", 
        facet_col="ArrestPerc",      # Creates a separate plot for each ArrestPerc
        facet_col_wrap=3,            # Arranges plots in a grid (3 columns wide)
        markers=True,                # Adds markers to the lines
        title="Total Members over Ticks by Arrest Percentage",
        labels={
            "tick": "Tick", 
            "revenues": "Revenues",
            "ArrestPerc": "Arrest %"
        }
    )

    fig_revenues.update_layout(height=1000)
    fig_revenues.show()
    return


app._unparsable_cell(
    r"""
        import marimo as mo
    """,
    name="_"
)


if __name__ == "__main__":
    app.run()
