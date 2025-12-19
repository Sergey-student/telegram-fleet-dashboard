import dash
from dash import dcc, html, dash_table, Input, Output, State, callback
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import base64
import io
import numpy as np
import traceback
from datetime import datetime

# Инициализация приложения
app = dash.Dash(__name__)
server = app.server

# Создаем пример данных для отображения при запуске
sample_data = pd.DataFrame({
    'date': pd.date_range('2024-01-01', periods=5, freq='MS'),
    'vehicle_id': ['V001', 'V002', 'V003', 'V004', 'V005'],
    'vehicle_type': ['Грузовой', 'Легковой', 'Микроавтобус', 'Грузовой', 'Легковой'],
    'mileage': [125000, 189500, 75600, 162300, 32500],
    'fuel_consumption': [22.5, 8.2, 14.3, 20.8, 7.5],
    'fuel_cost': [85000, 45000, 62000, 92000, 28000],
    'maintenance_cost': [15000, 8000, 12000, 18000, 5000],
    'maintenance_status': ['Исправен', 'Требуется ТО', 'Исправен', 'На ремонте', 'Исправен'],
    'status': ['В работе', 'В работе', 'В работе', 'На ремонте', 'В работе'],
    'vehicle_age': [3, 5, 2, 4, 1]
})

app.layout = html.Div([
    # Заголовок
    html.H1("🚗 Управление автопарком", 
            style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '30px'}),
    
    # Загрузка файла
    html.Div([
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                '📁 Перетащите или ',
                html.A('выберите CSV файл с данными автопарка')
            ]),
            style={
                'width': '100%', 'height': '60px', 'lineHeight': '60px',
                'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
                'textAlign': 'center', 'margin': '10px', 'backgroundColor': '#f8f9fa'
            },
            multiple=False
        ),
        html.P("Или используйте пример данных:", style={'textAlign': 'center', 'marginTop': '10px'}),
        html.Button("Загрузить пример данных", id="load-sample", n_clicks=0,
                   style={'margin': '10px auto', 'display': 'block', 'padding': '10px 20px'})
    ], style={'width': '50%', 'margin': 'auto'}),
    
    # Выбор периода анализа
    html.Div([
        html.Label("📅 Выберите период анализа:", style={'fontWeight': 'bold'}),
        dcc.Dropdown(
            id='period-selector',
            options=[
                {'label': 'Год', 'value': 'year'},
                {'label': 'Месяц', 'value': 'month'},
                {'label': 'Квартал', 'value': 'quarter'},
                {'label': 'Неделя', 'value': 'week'}
            ],
            value='month',
            style={'width': '200px', 'margin': '10px'}
        )
    ], style={'margin': '20px', 'textAlign': 'center'}),
    
    # Ключевые показатели (KPI)
    html.Div([
        html.Div([
            html.H4(id='total-vehicles', children="5"),
            html.P("Всего ТС в автопарке")
        ], className='indicator', style={'padding': '20px', 'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 'borderRadius': '10px', 'textAlign': 'center', 'color': 'white'}),
        
        html.Div([
            html.H4(id='avg-mileage', children="117,180 км"),
            html.P("Средний пробег")
        ], className='indicator', style={'padding': '20px', 'background': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', 'borderRadius': '10px', 'textAlign': 'center', 'color': 'white'}),
        
        html.Div([
            html.H4(id='utilization-rate', children="85%"),
            html.P("Коэффициент использования")
        ], className='indicator', style={'padding': '20px', 'background': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', 'borderRadius': '10px', 'textAlign': 'center', 'color': 'white'}),
        
        html.Div([
            html.H4(id='total-costs', children="452,000 ₽"),
            html.P("Общие затраты")
        ], className='indicator', style={'padding': '20px', 'background': 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', 'borderRadius': '10px', 'textAlign': 'center', 'color': 'white'})
    ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(4, 1fr)', 'gap': '20px', 'margin': '20px'}),
    
    # Графики
    html.Div([
        dcc.Graph(id='mileage-trend'),
        dcc.Graph(id='vehicle-type-distribution'),
        dcc.Graph(id='fuel-consumption'),
        dcc.Graph(id='maintenance-status'),
        dcc.Graph(id='cost-breakdown', style={'gridColumn': 'span 2'}),
        dcc.Graph(id='age-vs-mileage', style={'gridColumn': 'span 2'})
    ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(2, 1fr)', 'gap': '20px', 'margin': '20px'}),
    
    # Таблица с деталями
    html.Div([
        html.H3("📋 Детальная информация по транспортным средствам"),
        html.Div(id='data-info', style={'margin': '10px 0', 'color': '#666'}),
        html.Div(id='error-message', style={'margin': '10px 0', 'color': '#d32f2f', 'display': 'none'}),
        dash_table.DataTable(
            id='vehicles-table',
            page_size=10,
            style_table={'overflowX': 'auto', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'},
            style_cell={
                'textAlign': 'left', 
                'padding': '12px',
                'minWidth': '100px',
                'fontFamily': 'Arial'
            },
            style_header={
                'backgroundColor': '#1a237e', 
                'color': 'white', 
                'fontWeight': 'bold',
                'fontSize': '14px'
            },
            style_data_conditional=[
                {
                    'if': {'filter_query': '{status} = "На ремонте"'},
                    'backgroundColor': '#ffebee',
                    'color': '#c62828'
                },
                {
                    'if': {'filter_query': '{status} = "В работе"'},
                    'backgroundColor': '#e8f5e9',
                    'color': '#2e7d32'
                },
                {
                    'if': {'filter_query': '{maintenance_status} = "Требуется ТО"'},
                    'backgroundColor': '#fff3e0',
                    'color': '#ef6c00'
                },
                {
                    'if': {'column_id': 'fuel_consumption', 'filter_query': '{fuel_consumption} > 20'},
                    'backgroundColor': '#ffebee',
                    'fontWeight': 'bold'
                }
            ]
        )
    ], style={'margin': '20px', 'padding': '20px', 'background': '#f5f5f5', 'borderRadius': '10px'}),

    # Скрытое хранилище для данных
    dcc.Store(id='stored-data')
], style={'fontFamily': 'Arial, sans-serif', 'padding': '20px', 'maxWidth': '1400px', 'margin': 'auto'})

# Функция для парсинга CSV
def parse_contents(contents, filename):
    if contents is None:
        return None
    
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        if 'csv' in filename.lower():
            # Пробуем разные кодировки
            encodings = ['utf-8', 'utf-8-sig', 'cp1251', 'latin1']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(io.StringIO(decoded.decode(encoding)))
                    print(f"Файл успешно прочитан с кодировкой {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    print(f"Ошибка при чтении с кодировкой {encoding}: {e}")
                    continue
            
            if df is None:
                # Пробуем прочитать без указания кодировки
                try:
                    df = pd.read_csv(io.BytesIO(decoded))
                except Exception as e:
                    print(f"Ошибка при чтении файла: {e}")
                    return None
            
            # Проверяем, что DataFrame не пустой
            if df.empty:
                print("DataFrame пустой после чтения")
                return None
            
            # Преобразование даты
            date_columns = ['date', 'last_service_date', 'next_service_date']
            for col in date_columns:
                if col in df.columns:
                    try:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                    except Exception as e:
                        print(f"Ошибка при преобразовании даты в колонке {col}: {e}")
            
            # Заполнение пропущенных значений
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                df[col] = df[col].fillna(df[col].mean() if not df[col].isnull().all() else 0)
            
            # Заполнение текстовых колонок
            text_cols = df.select_dtypes(include=['object']).columns
            for col in text_cols:
                df[col] = df[col].fillna('Не указано')
            
            print(f"Успешно загружено {len(df)} строк, {len(df.columns)} колонок")
            print(f"Колонки: {list(df.columns)}")
            
            return df
            
    except Exception as e:
        print(f"Критическая ошибка при парсинге файла: {e}")
        traceback.print_exc()
        return None
    
    return None

# Callback для загрузки данных
@app.callback(
    [Output('stored-data', 'data'),
     Output('error-message', 'children'),
     Output('error-message', 'style')],
    [Input('upload-data', 'contents'),
     Input('load-sample', 'n_clicks')],
    [State('upload-data', 'filename')]
)
def update_stored_data(contents, n_clicks, filename):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return sample_data.to_dict('records'), "", {'display': 'none'}
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'upload-data' and contents is not None:
        df = parse_contents(contents, filename)
        if df is not None and not df.empty:
            return df.to_dict('records'), "", {'display': 'none'}
        else:
            error_msg = "Не удалось загрузить файл. Проверьте формат CSV файла."
            return dash.no_update, error_msg, {'display': 'block', 'color': '#d32f2f', 'padding': '10px', 'background': '#ffebee', 'borderRadius': '5px'}
    
    elif trigger_id == 'load-sample':
        return sample_data.to_dict('records'), "", {'display': 'none'}
    
    return sample_data.to_dict('records'), "", {'display': 'none'}

# Основной callback для обновления дашборда
@app.callback(
    [Output('mileage-trend', 'figure'),
     Output('vehicle-type-distribution', 'figure'),
     Output('fuel-consumption', 'figure'),
     Output('maintenance-status', 'figure'),
     Output('cost-breakdown', 'figure'),
     Output('age-vs-mileage', 'figure'),
     Output('vehicles-table', 'data'),
     Output('vehicles-table', 'columns'),
     Output('total-vehicles', 'children'),
     Output('avg-mileage', 'children'),
     Output('utilization-rate', 'children'),
     Output('total-costs', 'children'),
     Output('data-info', 'children')],
    [Input('stored-data', 'data'),
     Input('period-selector', 'value')]
)
def update_dashboard(stored_data, period):
    try:
        if stored_data is None or len(stored_data) == 0:
            # Возвращаем пустые графики если нет данных
            empty_fig = go.Figure()
            empty_fig.update_layout(
                title="Нет данных для отображения",
                xaxis_title="",
                yaxis_title="",
                annotations=[dict(
                    text="Загрузите данные для отображения",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )]
            )
            return [empty_fig] * 6 + [[], [], "0", "0 км", "0%", "0 ₽", "Нет данных"]
        
        # Преобразуем данные обратно в DataFrame
        df = pd.DataFrame(stored_data)
        
        # Информация о данных
        vehicle_count = df['vehicle_id'].nunique() if 'vehicle_id' in df.columns else len(df)
        data_info = f"Загружено {len(df)} записей, {vehicle_count} уникальных ТС"
        
        # Создание периодов для агрегации
        if 'date' in df.columns:
            try:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                df = df.dropna(subset=['date'])  # Удаляем строки с некорректными датами
                
                # Создаем периоды агрегации
                df['year'] = df['date'].dt.year.astype(str)
                df['month'] = df['date'].dt.strftime('%Y-%m')
                df['quarter'] = df['date'].dt.to_period('Q').astype(str)
                df['week'] = df['date'].dt.isocalendar().week.astype(str) + '-' + df['date'].dt.year.astype(str)
            except Exception as e:
                print(f"Ошибка при обработке дат: {e}")
        
        # Устанавливаем период по умолчанию если колонка даты отсутствует
        if period == 'year' and 'year' in df.columns:
            period_col = 'year'
        elif period == 'month' and 'month' in df.columns:
            period_col = 'month'
        elif period == 'quarter' and 'quarter' in df.columns:
            period_col = 'quarter'
        elif period == 'week' and 'week' in df.columns:
            period_col = 'week'
        else:
            # Если нет даты, используем vehicle_id как группировку
            period_col = 'vehicle_id' if 'vehicle_id' in df.columns else 'index'
            if period_col == 'index':
                df['index'] = range(len(df))
        
        # 1. График динамики пробега
        trend_fig = go.Figure()
        if 'mileage' in df.columns and period_col in df.columns:
            try:
                mileage_agg = df.groupby(period_col)['mileage'].mean().reset_index()
                if not mileage_agg.empty:
                    trend_fig = px.line(
                        mileage_agg, 
                        x=period_col, 
                        y='mileage',
                        title='📈 Динамика среднего пробега',
                        labels={'mileage': 'Средний пробег (км)', period_col: 'Период'},
                        markers=True
                    )
                    trend_fig.update_traces(line_color='#1e88e5', line_width=3)
                    trend_fig.update_layout(hovermode='x unified')
            except Exception as e:
                print(f"Ошибка при создании графика пробега: {e}")
        
        # 2. Распределение по типам ТС
        pie_fig = go.Figure()
        if 'vehicle_type' in df.columns:
            try:
                type_counts = df['vehicle_type'].value_counts().reset_index()
                type_counts.columns = ['vehicle_type', 'count']
                if not type_counts.empty:
                    pie_fig = px.pie(
                        type_counts,
                        values='count',
                        names='vehicle_type',
                        title='🚘 Распределение по типам ТС',
                        hole=0.3,
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    pie_fig.update_traces(textposition='inside', textinfo='percent+label')
            except Exception as e:
                print(f"Ошибка при создании круговой диаграммы: {e}")
        
        # 3. Расход топлива по типам ТС
        fuel_fig = go.Figure()
        if 'fuel_consumption' in df.columns and 'vehicle_type' in df.columns:
            try:
                fuel_agg = df.groupby('vehicle_type')['fuel_consumption'].mean().reset_index()
                if not fuel_agg.empty:
                    fuel_fig = px.bar(
                        fuel_agg.sort_values('fuel_consumption', ascending=False),
                        x='vehicle_type',
                        y='fuel_consumption',
                        title='⛽ Средний расход топлива по типам ТС',
                        labels={'fuel_consumption': 'Расход (л/100км)', 'vehicle_type': 'Тип ТС'},
                        color='fuel_consumption',
                        color_continuous_scale='RdYlGn_r'
                    )
                    fuel_fig.update_layout(xaxis_tickangle=-45)
            except Exception as e:
                print(f"Ошибка при создании графика расхода топлива: {e}")
        
        # 4. Статус технического обслуживания
        status_fig = go.Figure()
        if 'maintenance_status' in df.columns:
            try:
                status_counts = df['maintenance_status'].value_counts().reset_index()
                status_counts.columns = ['status', 'count']
                if not status_counts.empty:
                    colors = {'Исправен': '#4caf50', 'Требуется ТО': '#ff9800', 'На ремонте': '#f44336'}
                    status_fig = px.bar(
                        status_counts,
                        x='status',
                        y='count',
                        title='🔧 Статус технического обслуживания',
                        labels={'count': 'Количество ТС', 'status': 'Статус'},
                        color='status',
                        color_discrete_map=colors
                    )
                    status_fig.update_layout(showlegend=False)
            except Exception as e:
                print(f"Ошибка при создании графика статусов: {e}")
        
        # 5. Структура затрат
        cost_fig = go.Figure()
        cost_columns = ['fuel_cost', 'maintenance_cost']
        available_cost_cols = [col for col in cost_columns if col in df.columns]
        
        if available_cost_cols:
            try:
                costs = {}
                for col in available_cost_cols:
                    cost_name = 'Топливо' if 'fuel' in col else 'Ремонт'
                    costs[cost_name] = df[col].sum()
                
                if costs:
                    cost_df = pd.DataFrame(list(costs.items()), columns=['category', 'amount'])
                    cost_fig = px.pie(
                        cost_df,
                        values='amount',
                        names='category',
                        title='💰 Структура затрат',
                        hole=0.4,
                        color_discrete_sequence=['#FF6B6B', '#4ECDC4']
                    )
                    cost_fig.update_traces(textposition='inside', textinfo='percent+label')
            except Exception as e:
                print(f"Ошибка при создании графика затрат: {e}")
        
        # 6. Зависимость пробега от возраста
        scatter_fig = go.Figure()
        if all(col in df.columns for col in ['vehicle_age', 'mileage']):
            try:
                scatter_fig = px.scatter(
                    df,
                    x='vehicle_age',
                    y='mileage',
                    color='vehicle_type' if 'vehicle_type' in df.columns else None,
                    size='fuel_consumption' if 'fuel_consumption' in df.columns else None,
                    title='📊 Зависимость пробега от возраста ТС',
                    labels={'vehicle_age': 'Возраст (лет)', 'mileage': 'Пробег (км)'},
                    hover_data=['vehicle_id'] if 'vehicle_id' in df.columns else None,
                    trendline='ols'
                )
                scatter_fig.update_traces(marker=dict(opacity=0.7, line=dict(width=1, color='DarkSlateGrey')))
            except Exception as e:
                print(f"Ошибка при создании scatter графика: {e}")
        
        # Подготовка данных для таблицы
        table_data = df.to_dict('records')
        
        # Форматирование колонок для таблицы
        table_columns = []
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                column_def = {
                    'name': col,
                    'id': col,
                    'type': 'numeric',
                    'format': {'specifier': ',.0f'} if 'cost' in col.lower() or 'mileage' in col.lower() else {'specifier': ',.1f'}
                }
            else:
                column_def = {'name': col, 'id': col}
            table_columns.append(column_def)
        
        # Расчет показателей KPI
        total_vehicles = str(df['vehicle_id'].nunique()) if 'vehicle_id' in df.columns else str(len(df))
        
        avg_mileage = "Н/Д"
        if 'mileage' in df.columns and not df['mileage'].isnull().all():
            avg_mileage_value = df['mileage'].mean()
            avg_mileage = f"{avg_mileage_value:,.0f} км" if not pd.isna(avg_mileage_value) else "Н/Д"
        
        # Коэффициент использования
        utilization_rate = "Н/Д"
        if 'status' in df.columns:
            working = df[df['status'].astype(str).str.contains('работе', case=False, na=False)].shape[0]
            total = len(df)
            utilization = (working / total * 100) if total > 0 else 0
            utilization_rate = f"{utilization:.1f}%"
        
        # Общие затраты
        total_costs = 0
        if 'fuel_cost' in df.columns:
            total_costs += df['fuel_cost'].sum()
        if 'maintenance_cost' in df.columns:
            total_costs += df['maintenance_cost'].sum()
        
        total_costs_display = f"{total_costs:,.0f} ₽" if total_costs > 0 else "Н/Д"
        
        return [trend_fig, pie_fig, fuel_fig, status_fig, cost_fig, scatter_fig, 
                table_data, table_columns, total_vehicles, avg_mileage, 
                utilization_rate, total_costs_display, data_info]
        
    except Exception as e:
        print(f"Критическая ошибка в update_dashboard: {e}")
        traceback.print_exc()
        
        # Возвращаем пустые графики при ошибке
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="Ошибка при обработке данных",
            annotations=[dict(
                text="Произошла ошибка при обработке данных",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )]
        )
        
        return [empty_fig] * 6 + [[], [], "Ошибка", "Ошибка", "Ошибка", "Ошибка", f"Ошибка: {str(e)}"]

if __name__ == '__main__':
    app.run(
        debug=True,
        dev_tools_hot_reload=False,  # Отключаем hot reload для стабильности
        dev_tools_ui=True,
        dev_tools_props_check=True,
        host='127.0.0.1',
        port=8050
    )
