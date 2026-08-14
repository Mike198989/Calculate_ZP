import json
import os
from datetime import datetime
import flet as ft

# ==============================================================================
# 1. ЛОГИКА РАСЧЕТА ЗАРАБОТНОЙ ПЛАТЫ
# ==============================================================================

def calculate_salary(
    hourly_rate: float,
    days_worked_normal: float,
    days_pre_holiday_reduced: float = 0,
    days_pre_holiday_reduced_evening: float = 0,
    evening_shifts: float = 0,
    hours_overtime_first_two: float = 0,
    hours_overtime_after_two: float = 0,
    hours_weekend_holiday: float = 0,
    days_non_working_holiday: float = 0,
    hours_night: float = 0,
    overtime_multiplier_first_two_hours: float = 1.5,
    overtime_multiplier_after_two_hours: float = 2.0,
    weekend_holiday_multiplier: float = 2.0,
    non_working_holiday_multiplier: float = 1.0,
    night_surcharge_percent: float = 0.20,
    evening_surcharge_percent: float = 0.20,
    hazard_surcharge_percent: float = 0.12,
    difficulty_surcharge_percent: float = 0.10,
    ndfl_rate: float = 0.13,
    bonus_percent_of_base_hours: float = 0.0,
    **kwargs
) -> dict:
    for key, val in locals().items():
        if isinstance(val, (int, float)) and val < 0:
            raise ValueError(f"Параметр '{key}' не может быть отрицательным.")

    hours_worked_scheduled_full = days_worked_normal * 8
    hours_reduction_total = days_pre_holiday_reduced * 1.0
    hours_worked_normal = hours_worked_scheduled_full - hours_reduction_total

    if hours_worked_normal < 0:
        raise ValueError("Общее количество рабочих часов не может быть отрицательным.")

    hours_evening_scheduled_full = evening_shifts * 8
    hours_evening_reduction = days_pre_holiday_reduced_evening * 1.0
    hours_evening = hours_evening_scheduled_full - hours_evening_reduction

    if hours_evening < 0:
        raise ValueError("Количество вечерних часов не может быть отрицательным.")
    if days_pre_holiday_reduced_evening > days_pre_holiday_reduced:
        raise ValueError("Сокращенные вечерние дни не могут превышать общее количество сокращенных дней.")
    if days_pre_holiday_reduced_evening > evening_shifts:
        raise ValueError("Сокращенные вечерние дни не могут превышать количество вечерних смен.")

    hourly_pay_base = hourly_rate * hours_worked_normal
    evening_surcharge_amount = hourly_rate * hours_evening * evening_surcharge_percent
    hazard_surcharge_amount = hourly_rate * hours_worked_normal * hazard_surcharge_percent
    difficulty_surcharge_amount = hourly_rate * hours_worked_normal * difficulty_surcharge_percent
    night_surcharge_amount = hourly_rate * hours_night * night_surcharge_percent

    rate_with_hazard_surcharge = hourly_rate * (1 + hazard_surcharge_percent)

    overtime_payment_first_two = 0
    overtime_payment_after_two = 0

    if hours_overtime_first_two > 0:
        overtime_base_pay_first_two = hours_overtime_first_two * rate_with_hazard_surcharge
        overtime_payment_first_two = overtime_base_pay_first_two * overtime_multiplier_first_two_hours

    if hours_overtime_after_two > 0:
        overtime_base_pay_after_two = hours_overtime_after_two * rate_with_hazard_surcharge
        overtime_payment_after_two = overtime_base_pay_after_two * overtime_multiplier_after_two_hours

    total_overtime_payment = overtime_payment_first_two + overtime_payment_after_two

    weekend_holiday_pay = 0
    if hours_weekend_holiday > 0:
        weekend_holiday_pay = hours_weekend_holiday * rate_with_hazard_surcharge * weekend_holiday_multiplier

    hours_non_working_holiday = days_non_working_holiday * 8
    non_working_holiday_pay = 0
    if hours_non_working_holiday > 0:
        non_working_holiday_pay = hours_non_working_holiday * hourly_rate * non_working_holiday_multiplier

    base_for_bonus_calculation = (hourly_rate * hours_worked_normal) + \
                                 (hourly_rate * hours_evening * evening_surcharge_percent) + \
                                 (hourly_rate * hours_worked_normal * hazard_surcharge_percent) + \
                                 (hourly_rate * hours_overtime_first_two * (1 + hazard_surcharge_percent)) + \
                                 (hourly_rate * hours_overtime_after_two * (1 + hazard_surcharge_percent)) + \
                                 (hourly_rate * hours_weekend_holiday * (1 + hazard_surcharge_percent))

    bonus_amount = 0
    if bonus_percent_of_base_hours > 0 and base_for_bonus_calculation > 0:
        bonus_amount = base_for_bonus_calculation * bonus_percent_of_base_hours

    gross_salary = hourly_pay_base + \
                   bonus_amount + \
                   evening_surcharge_amount + \
                   hazard_surcharge_amount + \
                   difficulty_surcharge_amount + \
                   total_overtime_payment + \
                   weekend_holiday_pay + \
                   non_working_holiday_pay + \
                   night_surcharge_amount

    ndfl_amount = gross_salary * ndfl_rate
    net_salary = gross_salary - ndfl_amount

    breakdown = {}
    if hourly_pay_base > 0:
        breakdown[f"Базовые часы ({hours_worked_normal:.1f} ч)"] = hourly_pay_base
    if hours_reduction_total > 0:
        breakdown[f"Сокращение часов (-{hours_reduction_total:.1f} ч)"] = 0.00
    if bonus_amount > 0:
        breakdown["Премия"] = bonus_amount
    if hours_evening_scheduled_full > 0:
        breakdown[f"Вечерние часы ({hours_evening:.1f} ч)"] = evening_surcharge_amount
    if hazard_surcharge_amount > 0:
        breakdown["Доплата за вредность"] = hazard_surcharge_amount
    if difficulty_surcharge_amount > 0:
        breakdown["Доплата за сложность"] = difficulty_surcharge_amount
    if (hours_overtime_first_two + hours_overtime_after_two) > 0:
        breakdown["Сверхурочные"] = total_overtime_payment
    if hours_weekend_holiday > 0:
        breakdown["Выходные/праздники (часы)"] = weekend_holiday_pay
    if days_non_working_holiday > 0:
        breakdown["Праздничные дни"] = non_working_holiday_pay
    if hours_night > 0:
        breakdown["Ночные часы"] = night_surcharge_amount

    breakdown["Сумма до вычета (гросс)"] = gross_salary
    breakdown[f"НДФЛ ({ndfl_rate*100:.0f}%)"] = -ndfl_amount
    breakdown["Итого к выплате (нетто)"] = net_salary

    return {
        "gross_salary": round(gross_salary, 2),
        "ndfl_amount": round(ndfl_amount, 2),
        "net_salary": round(net_salary, 2),
        "breakdown": breakdown
    }

# Вспомогательный форматтер валюты в российском стиле (100 000,00 ₽)
def format_rub(val: float) -> str:
    sign = "-" if val < 0 else ""
    val = abs(val)
    int_part = f"{int(round(val * 100) // 100):,}".replace(",", " ")
    dec_part = f"{round(val % 1, 2):.2f}"[2:]
    return f"{sign}{int_part},{dec_part} ₽"

# ==============================================================================
# 2. ИНТЕРФЕЙС FLET
# ==============================================================================

def main(page: ft.Page):
    page.title = "Калькулятор ЗП"
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 16
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE, use_material3=True)

    settings_file = "app_settings.json"
    last_input_file = "last_input.json"
    history_file = "salary_history.json"

    default_coefficients = {
        "hourly_rate": 344.81,
        "overtime_multiplier_first_two_hours": 1.5,
        "overtime_multiplier_after_two_hours": 2.0,
        "weekend_holiday_multiplier": 2.0,
        "non_working_holiday_multiplier": 1.0,
        "night_surcharge_percent": 0.20,
        "evening_surcharge_percent": 0.20,
        "hazard_surcharge_percent": 0.12,
        "difficulty_surcharge_percent": 0.10,
        "ndfl_rate": 0.13,
        "bonus_percent_of_base_hours": 0.95,
        "theme_mode": "system"
    }

    coefficients = default_coefficients.copy()
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                coefficients.update(loaded)
        except Exception:
            pass

    saved_theme = coefficients.get("theme_mode", "system")
    if saved_theme == "dark":
        page.theme_mode = ft.ThemeMode.DARK
    elif saved_theme == "light":
        page.theme_mode = ft.ThemeMode.LIGHT
    else:
        page.theme_mode = ft.ThemeMode.SYSTEM

    def show_snack(text):
        sb = ft.SnackBar(content=ft.Text(text))
        try:
            page.open(sb)
        except Exception:
            page.snack_bar = sb
            sb.open = True
            page.update()

    inputs = {}
    steppers_controls = []
    
    fields_config = [
        ("days_worked_normal", "Отработано смен", "0", ft.Icons.WORK_OUTLINED, 1),
        ("evening_shifts", "Вечерних смен", "0", ft.Icons.BEDTIME_OUTLINED, 1),
        ("days_pre_holiday_reduced", "Сокращенные дни (всего)", "0", ft.Icons.TIMER_OFF_OUTLINED, 1),
        ("days_pre_holiday_reduced_evening", "Сокращенные вечерние", "0", ft.Icons.NIGHT_SHELTER_OUTLINED, 1),
        ("hours_overtime_first_two", "Переработка (первые 2ч)", "0", ft.Icons.MORE_TIME_OUTLINED, 1),
        ("hours_overtime_after_two", "Переработка (после 2ч)", "0", ft.Icons.ADD_ALARM_OUTLINED, 1),
        ("hours_weekend_holiday", "Часы в вых./праздники", "0", ft.Icons.EVENT_AVAILABLE_OUTLINED, 1),
        ("days_non_working_holiday", "Нерабочие прапздн. дни", "0", ft.Icons.CELEBRATION_OUTLINED, 1),
        ("hours_night", "Ночные часы", "0", ft.Icons.DARK_MODE_OUTLINED, 1),
    ]

    saved_inputs = {}
    if os.path.exists(last_input_file):
        try:
            with open(last_input_file, "r", encoding="utf-8") as f:
                saved_inputs = json.load(f)
        except Exception:
            pass

    def parse_float(field: ft.TextField) -> float:
        raw_val = field.value or ""
        val_str = raw_val.strip().replace(",", ".")
        if not val_str:
            return 0.0
        try:
            return float(val_str)
        except ValueError:
            field.border_color = "red"
            field.update()
            raise ValueError(f"Неверный формат числа в поле '{field.label}'")

    # Функция изменения значений кнопками + / -
    def create_stepper_field(key, label_text, default_val, icon, step=1):
        val = saved_inputs.get(key, default_val)
        tf = ft.TextField(
            label=label_text,
            value=str(val if val is not None else default_val),
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=icon,
            border_radius=12,
            height=54,
            expand=True,
            on_change=lambda e: auto_recalculate()
        )
        inputs[key] = tf

        def change_val(delta):
            try:
                cur = float(tf.value.replace(",", ".") or 0)
            except ValueError:
                cur = 0.0
            new_val = max(0.0, cur + delta)
            tf.value = str(int(new_val)) if new_val.is_integer() else f"{new_val:.1f}"
            tf.update()
            auto_recalculate()

        btn_minus = ft.IconButton(
            icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
            icon_color=ft.Colors.RED_400,
            on_click=lambda e: change_val(-step)
        )
        btn_plus = ft.IconButton(
            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
            icon_color=ft.Colors.BLUE_600,
            on_click=lambda e: change_val(step)
        )

        row = ft.Row([btn_minus, tf, btn_plus], alignment=ft.MainAxisAlignment.CENTER, spacing=0)
        return row

    steppers_dict = {}
    for key, label_text, default_val, icon, step in fields_config:
        steppers_dict[key] = create_stepper_field(key, label_text, default_val, icon, step)

    theme_dropdown = ft.Dropdown(
        label="Тема оформления",
        value=saved_theme,
        border_radius=12,
        options=[
            ft.dropdown.Option("system", "Системная"),
            ft.dropdown.Option("dark", "Темная"),
            ft.dropdown.Option("light", "Светлая"),
        ],
    )

    settings_inputs = {}
    coefficients_config = [
        ("hourly_rate", "Часовая ставка (руб.)", ft.Icons.MONETIZATION_ON_OUTLINED),
        ("overtime_multiplier_first_two_hours", "Множитель сверхурочных (1-2 ч)", ft.Icons.NUMBERS_OUTLINED),
        ("overtime_multiplier_after_two_hours", "Множитель сверхурочных (после 2 ч)", ft.Icons.NUMBERS_OUTLINED),
        ("weekend_holiday_multiplier", "Множитель вых./праздников (часы)", ft.Icons.NUMBERS_OUTLINED),
        ("non_working_holiday_multiplier", "Множитель праздничных дней", ft.Icons.NUMBERS_OUTLINED),
        ("night_surcharge_percent", "Доплата за ночь (доля, напр. 0.2)", ft.Icons.PERCENT_OUTLINED),
        ("evening_surcharge_percent", "Доплата за вечер (доля, напр. 0.2)", ft.Icons.PERCENT_OUTLINED),
        ("hazard_surcharge_percent", "Вредность (доля, напр. 0.12)", ft.Icons.PERCENT_OUTLINED),
        ("difficulty_surcharge_percent", "Сложность (доля, напр. 0.1)", ft.Icons.PERCENT_OUTLINED),
        ("ndfl_rate", "НДФЛ (доля, напр. 0.13)", ft.Icons.PERCENT_OUTLINED),
        ("bonus_percent_of_base_hours", "Премия от базы (доля, напр. 0.95)", ft.Icons.PERCENT_OUTLINED),
    ]

    for k, label_text, icon in coefficients_config:
        val = coefficients.get(k, 0)
        settings_inputs[k] = ft.TextField(
            label=label_text,
            value=str(val),
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=icon,
            border_radius=12,
            height=54,
            on_change=lambda e: auto_recalculate()
        )

    net_output = ft.Text("0,00 ₽", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    gross_output = ft.Text("Гросс: 0,00 ₽", size=13, color=ft.Colors.WHITE_70)
    ndfl_output = ft.Text("НДФЛ: 0,00 ₽", size=13, color=ft.Colors.WHITE_70)

    hero_card = ft.Card(
        elevation=4,
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text("К ВЫПЛАТЕ (НА РУКИ)", size=12, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE_70),
                    net_output,
                    ft.Divider(color=ft.Colors.WHITE_24, height=12),
                    ft.Row(
                        [gross_output, ndfl_output],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=4,
            ),
            padding=18,
            border_radius=16,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=["#1E88E5", "#1565C0", "#0D47A1"],
            ),
        ),
    )

    details_column = ft.Column(spacing=6)
    last_calc_result = {}

    def save_state():
        data = {k: v.value for k, v in inputs.items()}
        try:
            with open(last_input_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def auto_recalculate():
        nonlocal last_calc_result
        for field in inputs.values():
            field.border_color = None

        try:
            params = {k: parse_float(field) for k, field in inputs.items()}
            params.update(coefficients)
            result = calculate_salary(**params)
            last_calc_result = result

            net_output.value = format_rub(result['net_salary'])
            gross_output.value = f"Гросс: {format_rub(result['gross_salary'])}"
            ndfl_output.value = f"НДФЛ: {format_rub(result['ndfl_amount'])}"

            details_column.controls.clear()

            for name, val in result["breakdown"].items():
                is_summary = name in ["Сумма до вычета (гросс)", "Итого к выплате (нетто)"]
                text_color = ft.Colors.RED_400 if "НДФЛ" in name else (ft.Colors.GREEN_600 if is_summary else None)

                details_column.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Text(name, size=13, expand=True, weight=ft.FontWeight.BOLD if is_summary else ft.FontWeight.NORMAL),
                                ft.Text(
                                    format_rub(val), 
                                    size=13, 
                                    weight=ft.FontWeight.BOLD if is_summary else ft.FontWeight.W_500,
                                    color=text_color
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        padding=2
                    )
                )
            save_state()
            page.update()
        except ValueError:
            pass

    def copy_summary_click(e):
        if not last_calc_result or "breakdown" not in last_calc_result:
            show_snack("Сначала выполните расчёт")
            return
        
        lines = ["📊 Расчет заработной платы", "-----------------------------"]
        for k, v in last_calc_result["breakdown"].items():
            lines.append(f"{k}: {format_rub(v)}")
        text_summary = "\n".join(lines)
        
        page.set_clipboard(text_summary)
        show_snack("Результат скопирован в буфер обмена!")

    def save_to_history_click(e):
        if not last_calc_result or last_calc_result.get("net_salary", 0) == 0:
            show_snack("Нет данных для сохранения")
            return

        history_data = []
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
            except Exception:
                pass

        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        record = {
            "date": now_str,
            "net": last_calc_result["net_salary"],
            "gross": last_calc_result["gross_salary"],
            "ndfl": last_calc_result["ndfl_amount"],
            "inputs": {k: v.value for k, v in inputs.items()}
        }
        history_data.insert(0, record)

        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=4)
            show_snack("Сохранено в историю!")
            render_history()
        except Exception as err:
            show_snack(f"Ошибка сохранения истории: {err}")

    def save_settings_click(e):
        try:
            for k, tf in settings_inputs.items():
                raw_val = tf.value or ""
                val_str = raw_val.strip().replace(",", ".")
                if not val_str:
                    raise ValueError(f"Поле '{k}' не может быть пустым")
                val = float(val_str)
                if val < 0:
                    raise ValueError(f"Коэффициент '{k}' не может быть < 0")
                coefficients[k] = val
            
            selected_theme = theme_dropdown.value
            coefficients["theme_mode"] = selected_theme
            
            if selected_theme == "dark":
                page.theme_mode = ft.ThemeMode.DARK
            elif selected_theme == "light":
                page.theme_mode = ft.ThemeMode.LIGHT
            else:
                page.theme_mode = ft.ThemeMode.SYSTEM

            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(coefficients, f, ensure_ascii=False, indent=4)
            
            auto_recalculate()
            show_snack("Настройки сохранены!")
        except Exception as err:
            show_snack(f"Ошибка: {err}")

    def clear_click(e):
        for field in inputs.values():
            field.value = "0"
            field.border_color = None
        auto_recalculate()
        save_state()

    shifts_view = ft.Column([
        steppers_dict["days_worked_normal"],
        steppers_dict["evening_shifts"],
    ], spacing=12, visible=True)

    hours_view = ft.Column([
        steppers_dict["days_pre_holiday_reduced"],
        steppers_dict["days_pre_holiday_reduced_evening"],
        steppers_dict["hours_overtime_first_two"],
        steppers_dict["hours_overtime_after_two"],
        steppers_dict["hours_weekend_holiday"],
        steppers_dict["days_non_working_holiday"],
        steppers_dict["hours_night"],
    ], spacing=12, visible=False)

    history_column = ft.Column(spacing=8)
    history_view = ft.Column([
        ft.Text("Сохраненные расчеты", size=15, weight=ft.FontWeight.BOLD),
        history_column
    ], spacing=12, visible=False)

    def load_history_item(inputs_data):
        for k, v in inputs_data.items():
            if k in inputs:
                inputs[k].value = str(v)
        auto_recalculate()
        tab_segmented.selected = {"shifts"}
        set_tab("shifts")
        show_snack("Данные загружены из истории")

    def delete_history_item(index):
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
                if 0 <= index < len(history_data):
                    history_data.pop(index)
                    with open(history_file, "w", encoding="utf-8") as f:
                        json.dump(history_data, f, ensure_ascii=False, indent=4)
                    render_history()
            except Exception:
                pass

    def render_history():
        history_column.controls.clear()
        if not os.path.exists(history_file):
            history_column.controls.append(ft.Text("История пуста", color=ft.Colors.GREY_500, size=13))
            page.update()
            return

        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_data = json.load(f)
            if not history_data:
                history_column.controls.append(ft.Text("История пуста", color=ft.Colors.GREY_500, size=13))
            else:
                for idx, item in enumerate(history_data):
                    history_column.controls.append(
                        ft.Card(
                            elevation=1,
                            content=ft.Container(
                                content=ft.Row([
                                    ft.Column([
                                        ft.Text(item["date"], size=11, color=ft.Colors.GREY_600),
                                        ft.Text(format_rub(item["net"]), size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_600),
                                        ft.Text(f"Гросс: {format_rub(item['gross'])}", size=11, color=ft.Colors.GREY_600),
                                    ], expand=True, spacing=2),
                                    ft.IconButton(
                                        icon=ft.Icons.UPLOAD_FILE_OUTLINED, 
                                        tooltip="Загрузить в форму",
                                        on_click=lambda e, inp=item.get("inputs", {}): load_history_item(inp)
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE, 
                                        icon_color=ft.Colors.RED_400,
                                        tooltip="Удалить",
                                        on_click=lambda e, i=idx: delete_history_item(i)
                                    )
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                padding=10
                            )
                        )
                    )
        except Exception:
            history_column.controls.append(ft.Text("Ошибка чтения истории", color=ft.Colors.RED_400))
        page.update()

    settings_view = ft.Column([
        theme_dropdown,
        ft.Divider(),
        *[tf for tf in settings_inputs.values()],
        ft.ElevatedButton(
            "Сохранить настройки", 
            icon=ft.Icons.SAVE_OUTLINED, 
            on_click=save_settings_click, 
            height=48,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))
        )
    ], spacing=12, visible=False)

    # --------------------------------------------------------------------------
    # НАТИВНЫЙ ПЕРЕКЛЮЧАТЕЛЬ ВКЛАДОК Material 3 (SegmentedButton)
    # --------------------------------------------------------------------------
    def on_tab_change(e):
        selected_tab = list(e.data)[0] if isinstance(e.data, set) else list(tab_segmented.selected)[0]
        set_tab(selected_tab)

    def set_tab(tab_key):
        shifts_view.visible = (tab_key == "shifts")
        hours_view.visible = (tab_key == "hours")
        history_view.visible = (tab_key == "history")
        settings_view.visible = (tab_key == "settings")
        if tab_key == "history":
            render_history()
        page.update()

    tab_segmented = ft.SegmentedButton(
        selected={"shifts"},
        allow_multiple_selection=False,
        segments=[
            ft.Segment(value="shifts", label=ft.Text("Смены", size=11), icon=ft.Icon(ft.Icons.CALENDAR_MONTH_OUTLINED)),
            ft.Segment(value="hours", label=ft.Text("Часы", size=11), icon=ft.Icon(ft.Icons.ACCESS_TIME_OUTLINED)),
            ft.Segment(value="history", label=ft.Text("История", size=11), icon=ft.Icon(ft.Icons.HISTORY_OUTLINED)),
            ft.Segment(value="settings", label=ft.Text("Опции", size=11), icon=ft.Icon(ft.Icons.SETTINGS_OUTLINED)),
        ],
        on_change=on_tab_change,
    )

    forms_card = ft.Card(
        elevation=2,
        content=ft.Container(
            content=ft.Column([
                shifts_view,
                hours_view,
                history_view,
                settings_view,
            ]),
            padding=16,
            border_radius=14,
        )
    )

    details_card = ft.Card(
        elevation=1,
        content=ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, size=20, color=ft.Colors.BLUE),
                    ft.Text("Детализация расчёта", size=15, weight=ft.FontWeight.BOLD),
                ], spacing=8),
                ft.Divider(height=10),
                details_column,
                ft.Divider(height=10),
                ft.Row([
                    ft.OutlinedButton(
                        "Скопировать", 
                        icon=ft.Icons.COPY_OUTLINED, 
                        on_click=copy_summary_click,
                        expand=True,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                    ),
                    ft.OutlinedButton(
                        "В историю", 
                        icon=ft.Icons.BOOKMARK_BORDER_OUTLINED, 
                        on_click=save_to_history_click,
                        expand=True,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                    ),
                ], spacing=8)
            ]),
            padding=16,
            border_radius=14,
        )
    )

    header = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, size=28, color=ft.Colors.BLUE),
                ft.Text("Калькулятор ЗП", size=22, weight=ft.FontWeight.BOLD)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8
        ),
        padding=10
    )

    page.add(
        ft.Container(height=20),
        header,
        hero_card,
        ft.Row([tab_segmented], alignment=ft.MainAxisAlignment.CENTER),
        forms_card,
        ft.Row([
            ft.OutlinedButton(
                "Сбросить всё", 
                icon=ft.Icons.BACKSPACE_OUTLINED, 
                on_click=clear_click, 
                expand=True,
                height=46,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))
            ),
        ]),
        details_card
    )

    # Запуск авторасчета при старте для сохраненных данных
    auto_recalculate()

if __name__ == "__main__":
    ft.app(target=main)

