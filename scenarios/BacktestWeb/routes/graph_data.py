def _load_graph_market_data(
    symbol,
    start_date,
    end_date,
    intervalo,
    data_files_path,
    descargar_datos_func,
    dataframe_cls,
):
    simbolos_df = dataframe_cls([{'Symbol': symbol, 'Name': symbol}])
    stocks_data = descargar_datos_func(simbolos_df, start_date, end_date, intervalo, data_files_path)
    if stocks_data is None or stocks_data.empty:
        return None

    datos_filtrados = stocks_data[stocks_data['Symbol'] == symbol]
    if datos_filtrados.empty:
        return None

    return {symbol: datos_filtrados}


def _run_graph_backtest(
    stocks_data_dict,
    system_cls,
    config_final,
    symbol,
    run_backtest_func,
    logger,
):
    _, _, backtest_objects = run_backtest_func(
        stocks_data_dict,
        system_cls,
        config_final,
        [symbol],
        20,
        logger,
    )
    return (backtest_objects or {}).get(symbol)
