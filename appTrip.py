# ИМПОРТ БИБЛИОТЕК
import streamlit as st
import streamlit_antd_components as sac
import polars as pl
import altair as alt
import re
from pathlib import Path
from PIL import Image, ImageOps

# ФУНКЦИИ
def natural_sort_key(text: str):
    """Преобразует строку в список [текст, число, текст, число, ...] для правильной сортировки."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]
def get_photo_paths(folder: str) -> list[str]:
    folder_path = Path(folder)
    if not folder_path.is_dir():
        return [], []

    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    text_ext = {'.txt'}

    image_files = [
        f for f in folder_path.iterdir()
        if f.is_file() and f.suffix.lower() in image_extensions
    ]

    text_files = [t for t in folder_path.iterdir() if t.is_file() and t.suffix.lower() in text_ext]

    # Сортируем с использованием natural_sort_key
    image_sorted_files = sorted(image_files, key=lambda f: natural_sort_key(f.name))
    text_sorted_files = sorted(text_files, key=lambda t: natural_sort_key(t.name))

    return [str(f) for f in image_sorted_files], [str(t) for t in text_sorted_files]

# Построение графиков
def build_line_chart(df, metric):
    # Записываем словарь метрик
    metrics = {
        "distance_km": (
            "#4285b4",
            [
                alt.Tooltip("distance_km:Q", title="Расстояние, км.:"),
                alt.Tooltip("steps:Q", title="Шагов:")
            ],
            "Пройденное расстояние, км."
        ),
        "cats": ("#9B1827", [alt.Tooltip("cats:Q", title="Котиков:")], "Котиков увидено")
    }

    # Определяем поданную метрику
    significative = metrics[metric]

    # Находим длину DataFrame
    cnt_tick = df.shape[0]

    # Общие настройки tooltip
    config_tooltip = significative[1]
    config_tooltip.append(alt.Tooltip("day", title="День:"))

    # Общие настройки оси Ox
    axis_config_x = alt.Axis(
        #format="%m.%y",            # формат отображения
        tickCount=cnt_tick,         # шаг деления (Тут может подойти "month")
        title=None,                 # заголовок оси
        grid=False,                 # убрать сетку
        ticks=False,                # засечки оси
        domain=True,                # линия оси (включить или нет)
        domainColor="#cccccc",      # цвет оси
        labelColor="#2e2e2e",       # цвет значений на оси
        labelFont="Helvetica"       # шрифт оси
    )

    # Построение линии
    base_line = alt.Chart(df)\
        .mark_line(color=significative[0])\
        .encode(
            x=alt.X("day", axis=axis_config_x),
            y=alt.Y(f'{metric}:Q', axis=None),
            tooltip=config_tooltip
        )

    # Построение точек
    points = alt.Chart(df)\
        .mark_point(
            size=50,                 # размер точки
            filled=True,             # заполненный или пустой (круг или окружность)
            color='#ffffff',         # цвет внутренней области
            stroke=significative[0], # цвет контура
            opacity=1,               # прозрачность точки
            strokeWidth=2            # толщина линии контура
        )\
        .encode(
            x=alt.X("day", axis=axis_config_x),
            y=alt.Y(f'{metric}:Q', axis=None),
            tooltip=config_tooltip
        )

    # Отображаем все значения
    texts = alt.Chart(df).mark_text(
        align='center',  # горизонтальное выравнивание текста ('left', 'center', 'right')
        baseline='bottom',
        # вертикальное выравнивание текста относительно базовой линии ('top', 'middle', 'bottom', 'alphabetic')
        dy=-8,                  # вертикальное смещение текста в пикселях
        fontSize=14,            # размер шрифта
        fontWeight='bold',      # толщина шрифта ('normal', 'bold')
        font='Helvetica',       # шрифт
        color=significative[0]  # цвет текста
    )\
    .encode(
        x=alt.X("day", axis=axis_config_x),
        y=alt.Y(f'{metric}:Q', axis=None),
        text=alt.Text(f'{metric}:Q'),
        tooltip=config_tooltip
    )

    # Объединение слоёв
    chart = alt.layer(base_line, points, texts).properties(
        title=alt.TitleParams(
            text=significative[2],
            anchor='start',
            font='Helvetica',
            color="#2e2e2e",
            fontSize=16,
        ),
        width=352,
        height=198
    )\
    .configure_axisX(
        labelColor="#2E2E2E",
        labelFont="Helvetica"
    )

    return chart

# Построение графиков
def build_bar_chart(df):
    # Максимальное значение расходов
    max_value_cost = df.select("costs").max().item()

    bar_base = alt.Chart(st.session_state.df_expenses).mark_bar(color="#002f55")\
    .encode(
        x=alt.X(
            shorthand="costs:Q",
            title="Расходы, руб.",
            scale=alt.Scale(domain=[0, max_value_cost], nice=False),
            axis=alt.Axis(tickCount=5, format="d", labelFont="Helvetica")
        ),
        y=alt.Y(
            shorthand="category:N",
            title=None,
            sort="-x",
            axis=alt.Axis(labelFont="Helvetica", labelFontSize=12, labelLimit=500)
        ),
        tooltip=[
            alt.Tooltip("costs:Q", title="Расходы, руб.:"),
            alt.Tooltip("share:N", title="В процентах:"),
        ]
    )\
    .properties(
        title=alt.TitleParams(
            text="Расходы по категориям",
            anchor="middle",
            font="Helvetica"
        ),
        width=400,
        height=250
    )

    # Добавляем значения
    bar_txt = bar_base.mark_text(
        align="left",       # Выравниваем по левому краю
        baseline="middle",
        dx=5,
        fontSize=14,
        fontWeight='bold',
        font="Helvetica",
        color="#002f55"
    )\
    .encode(
        text=alt.Text("costs:Q", format=".0f"),
        x=alt.X("costs:Q", axis=None)
    )

    # Объединяем
    bar_total = alt.layer(bar_base, bar_txt)
    # Финальные настройки
    bar_chart = bar_total.properties(
        title=alt.TitleParams(
            text="Расходы по категориям, руб.",
            anchor="start",
            font="Helvetica",
            color="#2e2e2e",
            fontSize=16
        ),
        width=500,
        height=250
    )\
    .configure(background="#FFFAFA")\
    .configure_axisY(
        labelAlign="left",  # Выравнивание по левому краю
        labelPadding=120,   # Отступ для длинных подписей
        labelColor="#2E2E2E",
        labelFont="Helvetica"
    )

    return bar_chart

@st.cache_data(show_spinner=False)
def load_data():
    # Данные по шагам и котикам
    data = [
        {"День": 1, "Расстояние, км.": 6.9, "Расстояние, шаги": 10984, "Котики, шт.": 10},
        {"День": 2, "Расстояние, км.": 20.7, "Расстояние, шаги": 31469, "Котики, шт.": 119},
        {"День": 3, "Расстояние, км.": 9.1, "Расстояние, шаги": 12857, "Котики, шт.": 4},
        {"День": 4, "Расстояние, км.": 22.7, "Расстояние, шаги": 34433, "Котики, шт.": 0},
        {"День": 5, "Расстояние, км.": 20.9, "Расстояние, шаги": 31222, "Котики, шт.": 3},
        {"День": 6, "Расстояние, км.": 15.8, "Расстояние, шаги": 24161, "Котики, шт.": 0},
        {"День": 7, "Расстояние, км.": 7.9, "Расстояние, шаги": 12490, "Котики, шт.": 15},
        {"День": 8, "Расстояние, км.": 15.7, "Расстояние, шаги": 24320, "Котики, шт.": 16},
        {"День": 9, "Расстояние, км.": 16.9, "Расстояние, шаги": 25659, "Котики, шт.": 5},
        {"День": 10, "Расстояние, км.": 4.7, "Расстояние, шаги": 7349, "Котики, шт.": 4},
        {"День": 11, "Расстояние, км.": 5.3, "Расстояние, шаги": 8378, "Котики, шт.": 25},
        {"День": 12, "Расстояние, км.": 9.7, "Расстояние, шаги": 14702, "Котики, шт.": 72},
    ]
    # Получаем DataFrame по шагам и котикам
    df_cat_step = pl.DataFrame(data)
    # Переименовываем df_cat_step
    df_cat_step = df_cat_step.rename({
        "День": "day",
        "Расстояние, км.": "distance_km",
        "Расстояние, шаги": "steps",
        "Котики, шт.": "cats"
    })

    # Сводная таблица по расходам
    df_expenses = pl.DataFrame({
    "category": ["Прочее", "Развлечения и досуг", "Еда", "Жильё", "Транспорт"],
    "costs": [11495, 21713, 60634, 66832, 125794],
    "share": ["4%", "8%", "21%", "23%", "44%"]
})

    return df_cat_step, df_expenses

# КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(
    page_title="Дневник путешествия",
    page_icon=":material/travel:",
    layout="wide",
    initial_sidebar_state=None
)

# пути относительно файла appTrip.py, автоматически подстраивается под ОС
BASE_DIR = Path(__file__).parent

# СОСТОЯНИЯ
if "dict_test" not in st.session_state:
    st.session_state.dict_test = {str(x): BASE_DIR / "photo_days" / f"day{x}" for x in range(1, 13)}

if "all_data" not in st.session_state:
    st.session_state.all_data = True
if "df_cat_step" not in st.session_state:
    st.session_state.df_cat_step = None
if "df_expenses" not in st.session_state:
    st.session_state.df_expenses = None

if "data_viz" not in st.session_state:
    st.session_state.data_viz = True
if "ch1" not in st.session_state:
    st.session_state.ch1 = None
if "ch2" not in st.session_state:
    st.session_state.ch2 = None
if "ch3" not in st.session_state:
    st.session_state.ch3 = None

# Загружаем данные (формируем DataFrame)
if st.session_state.all_data:
    st.session_state.df_cat_step, st.session_state.df_expenses = load_data()
    st.session_state.all_data = False

# ФРОНТ
st.title("Дневник путешествия")
col1, col2 = st.columns([38, 62], border=False)
with col1:
    # Вызываем построения графиков
    if st.session_state.data_viz:
        st.session_state.ch1 = build_line_chart(st.session_state.df_cat_step, 'cats')
        st.session_state.ch2 = build_line_chart(st.session_state.df_cat_step, 'distance_km')
        st.session_state.ch3 = build_bar_chart(st.session_state.df_expenses)
        st.session_state.data_viz = False

    # Выбор графика
    chart_segment = sac.segmented(
        items=[
            sac.SegmentedItem(label="Котики"),
            sac.SegmentedItem(label="Шаги"),
            sac.SegmentedItem(label="Расходы"),
        ],
        label="Выбор графика",
        index=0,
        size="sm",
        radius="sm"
    )

    # Выводим график в зависимости от выбора
    if chart_segment == "Котики":
        st.altair_chart(st.session_state.ch1, width="stretch", height="content")
    elif chart_segment == "Шаги":
        st.altair_chart(st.session_state.ch2, width="stretch", height="content")
    else:
        st.altair_chart(st.session_state.ch3, width="stretch", height="content")

with col2:
    # Выбор дня
    days_segment = sac.segmented(
        items=[sac.SegmentedItem(label=str(x)) for x in range(1, 13)],
        label="День",
        index=0,
        size="sm",
        radius="sm"
    )

    # Получаем список путей к изображениям и тексту
    list_p, list_t = get_photo_paths(st.session_state.dict_test[days_segment])
    # Определяем количество фотографий
    cnt_pt = min(len(list_p), len(list_t))

    # Создаём вкладки
    tabs = st.tabs([str(x) for x in range(1, cnt_pt + 1)])
    # Отображаем соответсвующее фото в каждой вкладке
    for i, tab in enumerate(tabs):
        with tab:
            col1_tab, col2_tab = st.columns([50, 50])

            with col1_tab:
                with Image.open(list_p[i]) as img:
                    st.image(ImageOps.exif_transpose(img), width=400)

            with col2_tab:
                txt_path = list_t[i]
                with open(txt_path, "r", encoding="utf-8") as f:
                    content = f.read()

                st.markdown(f"""
                    <div 
                        style="background-color: #FFFAFA; 
                        padding: 20px; 
                        border-radius: 4px; 
                        text-align: left; 
                        font-style: italic; 
                        color: #2E2E2E;
                        white-space: pre-line;
                        margin: 0;
                        font-size: 14px;
                    ">
                    {content}
                    """, unsafe_allow_html=True
                )
