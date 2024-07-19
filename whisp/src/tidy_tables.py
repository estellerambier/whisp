import pandas as pd
from ..parameters.config_runtime import (
    percent_or_ha,
    cols_ind_1_treecover,
    cols_ind_2_commodities,
    cols_ind_3_dist_before_2020,
    cols_ind_4_dist_after_2020,
    geometry_area_column,
)
from .pd_schemas import DfGEEDatasetsType


def clamp(
    value: float | pd.Series, min_val: float, max_val: float
) -> float | pd.Series:
    """
    Clamp a value or a Pandas Series within a specified range.

    Args:
        value (float | pd.Series): The value or series to be clamped.
        min_val (float): The minimum value of the range.
        max_val (float): The maximum value of the range.

    Returns:
        float | pd.Series: The clamped value or series within the range.
    """
    if isinstance(value, pd.Series):
        return value.clip(lower=min_val, upper=max_val)
    else:
        return max(min_val, min(value, max_val))


def check_range(value: float) -> None:
    if not (0 <= value <= 100):
        raise ValueError("Value must be between 0 and 100.")


def whisp_risk(
    df: DfGEEDatasetsType,
    ind_1_pcent_threshold: float,
    ind_2_pcent_threshold: float,
    ind_3_pcent_threshold: float,
    ind_4_pcent_threshold: float,
    ind_1_input_columns: pd.Series = cols_ind_1_treecover,
    ind_2_input_columns: pd.Series = cols_ind_2_commodities,
    ind_3_input_columns: pd.Series = cols_ind_3_dist_before_2020,
    ind_4_input_columns: pd.Series = cols_ind_4_dist_after_2020,
    ind_1_name: str = "Indicator_1_treecover",
    ind_2_name: str = "Indicator_2_commodities",
    ind_3_name: str = "Indicator_3_disturbance_before_2020",
    ind_4_name: str = "Indicator_4_disturbance_after_2020",
    low_name: str = "no",
    high_name: str = "yes",
) -> DfGEEDatasetsType:
    """Adds the EUDR (European Union Deforestation Risk) column to the DataFrame based on indicator values.

    Args:
        df (DfGEEDatasetsType): Input DataFrame.
        ind_1_name (str, optional): Name of first indicator column. Defaults to "Indicator_1_treecover".
        ind_2_name (str, optional): Name of second indicator column. Defaults to "Indicator_2_commodities".
        ind_3_name (str, optional): Name of third indicator column. Defaults to "Indicator_3_disturbance_before_2020".
        ind_4_name (str, optional): Name of fourth indicator column. Defaults to "Indicator_4_disturbance_after_2020".
        low_name (str, optional): Value shown in table if less than or equal to threshold. Defualts to "no".
        high_name (str, optional): Value shown in table if more than threshold. Defualts to "yes".
    Returns:
        DfGEEDatasetsType: DataFrame with added 'EUDR_risk' column.
    """

    input_cols = [
        ind_1_input_columns,
        ind_2_input_columns,
        ind_3_input_columns,
        ind_4_input_columns,
    ]
    thresholds = [
        ind_1_pcent_threshold,
        ind_2_pcent_threshold,
        ind_3_pcent_threshold,
        ind_4_pcent_threshold,
    ]
    names = [ind_1_name, ind_2_name, ind_3_name]
    [check_range(threshold) for threshold in thresholds]

    df_w_indicators = add_indicators(
        df,
        input_cols,
        thresholds,
        names,
        low_name,
        high_name,
    )

    df_w_indicators_and_risk = add_eudr_risk_col(
        df=df_w_indicators,
        ind_1_name=ind_1_name,
        ind_2_name=ind_2_name,
        ind_3_name=ind_3_name,
        ind_4_name=ind_4_name,
    )

    return df_w_indicators_and_risk


def add_eudr_risk_col(
    df: DfGEEDatasetsType,
    ind_1_name: str,
    ind_2_name: str,
    ind_3_name: str,
    ind_4_name: str,
) -> DfGEEDatasetsType:
    """
    Adds the EUDR (European Union Deforestation Risk) column to the DataFrame based on indicator values.

    Args:
        df (DataFrame): Input DataFrame.
        ind_1_name (str): Name of first indicator column.
        ind_2_name (str): Name of second indicator column.
        ind_3_name (str): Name of third indicator column.
        ind_4_name (str): Name of fourth indicator column.

    Returns:
        DataFrame: DataFrame with added 'EUDR_risk' column.
    """

    for index, row in df.iterrows():
        # If any of the first three indicators suggest low risk, set EUDR_risk to "low"
        if (
            row[ind_1_name] == "no"
            or row[ind_2_name] == "yes"
            or row[ind_3_name] == "yes"
        ):
            df.at[index, "EUDR_risk"] = "low"
        # If none of the first three indicators suggest low risk and Indicator 4 suggests no risk, set EUDR_risk to "more_info_needed"
        elif row[ind_4_name] == "no":
            df.at[index, "EUDR_risk"] = "more_info_needed"
        # If none of the above conditions are met, set EUDR_risk to "high"
        else:
            df.at[index, "EUDR_risk"] = "high"

    return df


def add_indicators(
    df: DfGEEDatasetsType,
    input_cols: list[str],
    thresholds: list[float],
    names: list[str],
    low_name: str = "no",
    high_name: str = "yes",
) -> DfGEEDatasetsType:

    for input_col, threshold, name in zip(input_cols, thresholds, names):
        df = add_indicator_column(
            df=df,
            input_columns=input_col,
            threshold=threshold,
            new_column_name=name,
            low_name=low_name,
            high_name=high_name,
        )

    return df


def add_indicator_column(
    df: DfGEEDatasetsType,
    input_columns: list[str],
    threshold: float,
    new_column_name: str,
    low_name: str = "yes",
    high_name: str = "no",
    sum_comparison: bool = False,
) -> DfGEEDatasetsType:
    """
    Add a new column to the DataFrame based on the specified columns, threshold, and comparison sign.

    Parameters:
        df (DfGEEDatasetsType): The pandas DataFrame to which the column will be added.
        input_columns (list): List of column names to check for threshold.
        threshold (float): The threshold value to compare against.
        new_column_name (str): The name of the new column to be added.
        The '>' sign is used for comparisons.
        When 'sum comparison' == True, then the threshold is compared to the sum of all those listed in 'input_columns', as opposed to when Flalse, when each column in the list is compared to the threshold individually
        low_name (str): The name for the value when below or equal to threshold (default is 'no').
        high_name (str): The name for the value when above threshold (default is 'yes').
        sum_comparison (bool): If True, sum all values in input_columns and compare to threshold (default is False).

    Returns:
        DfGEEDatasetsType: The DataFrame with the new column added.
    """
    # Create a new column and initialize with low_name
    df[new_column_name] = low_name

    # if percent_or_ha == "ha": print ("output in hectares. Converting values to percent for indicator")

    # Default behavior: use '>' for single column comparison
    if sum_comparison:
        # Sum all values in specified columns and compare to threshold
        sum_values = df[input_columns].sum(axis=1)
        df.loc[sum_values > threshold, new_column_name] = high_name
    else:
        # Check if any values in specified columns are above the threshold and update the new column accordingly
        for col in input_columns:
            # So that threshold is always in percent, if outputs are in ha, the code converts to percent (based on dividing by the geometry_area_column column.
            # Clamping is needed due to differences in decimal places (meaning input values may go just over 100)
            if percent_or_ha == "ha":
                # if df[geometry_area_column]<0.01: #to add in for when points, some warning message or similar

                val_to_check = clamp(
                    ((df[col] / df[geometry_area_column]) * 100), 0, 100
                )
            else:
                val_to_check = df[col]
            df.loc[val_to_check > threshold, new_column_name] = high_name
    return df


def add_indicator_column_from_csv(
    csv_file,
    input_columns,
    threshold,
    new_column_name,
    low_name="low",
    high_name="high",
    sum_comparison=False,
    output_file=None,
):
    """
    Read a CSV file into a DataFrame, add a new column based on specified columns and threshold,
    and optionally export the DataFrame as a CSV file.

    Parameters:
        csv_file (str): The path to the CSV file.
        input_columns (list): List of column names to check for threshold.
        threshold (float): The threshold value above which the new column will be set.
        new_column_name (str): The name of the new column to be added.
        low_name (str): The name for the value when below the threshold (default is 'low').
        high_name (str): The name for the value when above the threshold (default is 'high').
        sum_comparison (bool): If True, sum all values in input_columns and compare to threshold (default is False).
        output_file (str, optional): The name of the CSV file to export the DataFrame (default is None).

    Returns:
        DataFrame or None: The DataFrame with the new column added if output_file is not provided, otherwise None.
    """
    # Read the CSV file into a DataFrame
    df = pd.read_csv(csv_file)

    # Call the add_indicator_column function
    df = add_indicator_column(
        df,
        input_columns,
        threshold,
        new_column_name,
        low_name,
        high_name,
        sum_comparison,
    )

    # Export the DataFrame as a CSV file if output_file is provided
    if output_file:
        df.to_csv(output_file, index=False)
        print(f"exported to {output_file}")
    else:
        return df


def create_wildcard_column_list(df, wildcard_patterns):
    """
    Create a list of column names based on multiple wildcard patterns.

    Parameters:
        df (DataFrame): The pandas DataFrame to search for columns.
        wildcard_patterns (list): List of wildcard patterns to match column names.

    Returns:
        list: List of column names matching the wildcard patterns.
    """
    column_lists = [
        df.filter(like=pattern).columns.tolist() for pattern in wildcard_patterns
    ]
    return [col for sublist in column_lists for col in sublist]


def select_years_in_range(string_list, min_year, max_year):
    """
    Select strings from the list where the last four characters, when turned into integers,
    are in the specified range of years.

    Parameters:
        string_list (list): List of strings.
        min_year (int): The minimum year of the range.
        max_year (int): The maximum year of the range.

    Returns:
        list: List of strings where the last four characters are in the specified range of years.
    """
    selected_strings = []
    for string in string_list:
        if len(string) >= 4:
            last_four_digits = string[-4:]
            try:
                year = int(last_four_digits)
                if year in range(min_year, max_year + 1):
                    selected_strings.append(string)
            except ValueError:
                pass
    return selected_strings


def order_list_from_lookup(lookup_gee_datasets_df):
    return lookup_gee_datasets_df.sort_values(by=["dataset_order"])[
        "dataset_name"
    ].tolist()  # names sorted by list


def create_column_list_from_lookup(lookup_gee_datasets_df, prefix_columns_list):
    # ordered_dataset_df= lookup_gee_datasets_df.sort_values(by=['dataset_order'])

    # column_order_list = list(ordered_dataset_df["dataset_name"])
    column_order_list = lookup_gee_datasets_df.sort_values(by=["dataset_order"])[
        "dataset_name"
    ].tolist()

    # adds in a list of columns to the start of the order list (i.e. the geo_id, geometry area column and country columns), if left blank nothing added
    column_order_list = prefix_columns_list + order_list_from_lookup(
        lookup_gee_datasets_df
    )

    return column_order_list


def reorder_columns_by_lookup(
    df,
    lookup_gee_datasets_df,
    dataset_order_column,
    dataset_name_column,
    prefix_columns_list=[],
):
    """reorder columns by creating an ordered list from a lookup_gee_datasets_df containing column order and dataset names that match those in results dataframe"""
    column_order_list = create_column_list_from_lookup(
        lookup_gee_datasets_df, prefix_columns_list
    )
    # ordered_dataset_df= lookup_gee_datasets_df.sort_values(by=['dataset_order'])

    # column_order_list = list(ordered_dataset_df["dataset_name"])

    # # adds in a list of columns to the start of the order list (i.e. the geo_id, geometry area column and country columns), if left blanmk nothing added
    # column_order_list = prefix_columns_list + column_order_list

    df_reordered = df.reindex(columns=column_order_list)  # reorder by list

    return df_reordered


def make_lookup_from_feature_col(
    feature_col,
    join_column,
    lookup_column,
    join_column_new_name=False,
    lookup_column_new_name=False,
):
    """makes a lookup table (pandas dataframe) from two columns in a feature collection (duplicates removed)"""

    list_join_column = feature_col.aggregate_array(join_column).getInfo()

    list_lookup_column = feature_col.aggregate_array(lookup_column).getInfo()

    # make dataframe from columns
    lookup_table = pd.DataFrame(
        {join_column: list_join_column, lookup_column: list_lookup_column}
    )
    # removes duplicates
    lookup_table = lookup_table.drop_duplicates()

    # rename columns if specified
    if join_column_new_name != False:
        lookup_table.rename(columns={join_column: join_column_new_name}, inplace=True)

    if lookup_column_new_name != False:
        lookup_table.rename(
            columns={lookup_column: lookup_column_new_name}, inplace=True
        )

    return lookup_table


def truncate_strings_in_list(input_list, max_length):
    """as name suggests, useful for exporting to shapefiles fort instance where col name length is limited"""
    return [string[:max_length] for string in input_list]


###alternative vedrsion for clarity
# If 'Treecover_indicator' is "no", or 'Commodities_indicator' is "yes", or 'Disturbance_before_2020_indicator' is "yes", then set 'EUDR_risk' to "low".
# If 'Disturbance_after_2020_indicator' is "yes", (and previous condition is not true), then set 'EUDR_risk' to "high".
# If none of the above conditions are met, set 'EUDR_risk' to "more_info_needed".

# def calculate_eudr_risk(df):
#     for index, row in df.iterrows():
#         if (row['Treecover_indicator'] == "no" or
#             row['Commodities_indicator'] == "yes" or
#             row['Disturbance_before_2020_indicator'] == "yes"):
#             df.at[index, 'EUDR_risk'] = "low"
#         elif row['Disturbance_after_2020_indicator'] == "yes":
#             df.at[index, 'EUDR_risk'] = "high"
#         else:
#             df.at[index, 'EUDR_risk'] = "more_info_needed"
#     return df