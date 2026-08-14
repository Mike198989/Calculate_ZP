import json
import os
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

    inputs = {}
    fields_config = [
        ("days_worked_normal", "Отработано смен (смен)", "0", ft.Icons.WORK_OUTLINED),
        ("evening_shifts", "Вечерних смен (смен)", "0", ft.Icons.BEDTIME_OUTLINED),
        ("days_pre_holiday_reduced", "Сокращенные дни (общее, дн.)", "0", ft.Icons.TIMER_OFF_OUTLINED),
        ("days_pre_holiday_reduced_evening", "Сокращенные вечерние смены (дн.)", "0", ft.Icons.NIGHT_SHELTER_OUTLINED),
        ("hours_overtime_first_two", "Переработка первые 2ч (ч)", "0", ft.Icons.MORE_TIME_OUTLINED),
        ("hours_overtime_after_two", "Переработка последующие (ч)", "0", ft.Icons.ADD_ALARM_OUTLINED),
        ("hours_weekend_holiday", "Часы в вых./праздники (ч)", "0", ft.Icons.EVENT_AVAILABLE_OUTLINED),
        ("days_non_working_holiday", "Нерабочие праздничные дни (дн.)", "0", ft.Icons.CELEBRATION_OUTLINED),
        ("hours_night", "Ночные часы (ч)", "0", ft.Icons.DARK_MODE_OUTLINED),
    ]

    saved_inputs = {}
    if os.path.exists(last_input_file):
        try:
            with open(last_input_file, "r", encoding="utf-8") as f:
                saved_inputs = json.load(f)
        except Exception:
            pass

    for key, label_text, default_val, icon in fields_config:
        val = saved_inputs.get(key, default_val)
        inputs[key] = ft.TextField(
            label=label_text,
            value=str(val if val is not None else default_val),
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=icon,
            border_radius=12,
            height=58,
        )

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
            height=58,
        )

    net_output = ft.Text("0.00 руб.", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    gross_output = ft.Text("Гросс: 0.00 руб.", size=13, color=ft.Colors.WHITE_70)
    ndfl_output = ft.Text("НДФЛ: 0.00 руб.", size=13, color=ft.Colors.WHITE_70)

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

    def show_snack(text):
        sb = ft.SnackBar(content=ft.Text(text))
        try:
            page.open(sb)
        except Exception:
            page.snack_bar = sb
            sb.open = True
            page.update()

    def save_state():
        data = {k: v.value for k, v in inputs.items()}
        try:
            with open(last_input_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
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
            
            page.update()
            show_snack("Настройки сохранены!")
        except Exception as err:
            show_snack(f"Ошибка в настройках: {err}")

    def calculate_click(e):
        for field in inputs.values():
            field.border_color = None

        try:
            params = {}
            for k, field in inputs.items():
                params[k] = parse_float(field)
            
            params.update(coefficients)
            result = calculate_salary(**params)

            net_output.value = f"{result['net_salary']:,.2f} руб."
            gross_output.value = f"Гросс: {result['gross_salary']:,.2f} руб."
            ndfl_output.value = f"НДФЛ: {result['ndfl_amount']:,.2f} руб."

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
                                    f"{val:,.2f} руб.", 
                                    size=13, 
                                    weight=ft.FontWeight.BOLD if is_summary else ft.FontWeight.W_500,
                                    color=text_color
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        padding=4
                    )
                )
            save_state()
            page.update()
        except ValueError as err:
            show_snack(f"{err}")

    def clear_click(e):
        for field in inputs.values():
            field.value = "0"
            field.border_color = None
        net_output.value = "0.00 руб."
        gross_output.value = "Гросс: 0.00 руб."
        ndfl_output.value = "НДФЛ: 0.00 руб."
        details_column.controls.clear()
        save_state()
        page.update()

    shifts_view = ft.Column([
        inputs["days_worked_normal"],
        inputs["evening_shifts"],
    ], spacing=12, visible=True)

    hours_view = ft.Column([
        inputs["days_pre_holiday_reduced"],
        inputs["days_pre_holiday_reduced_evening"],
        inputs["hours_overtime_first_two"],
        inputs["hours_overtime_after_two"],
        inputs["hours_weekend_holiday"],
        inputs["days_non_working_holiday"],
        inputs["hours_night"],
    ], spacing=12, visible=False)

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
    # НАДЕЖНОЕ ПЕРЕКЛЮЧЕНИЕ ВКЛАДОК
    # --------------------------------------------------------------------------
    active_btn_style = ft.ButtonStyle(
        bgcolor=ft.Colors.BLUE_600,
        color=ft.Colors.WHITE,
        shape=ft.RoundedRectangleBorder(radius=10)
    )
    inactive_btn_style = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=10)
    )

    btn_shifts = ft.ElevatedButton("Смены", icon=ft.Icons.CALENDAR_MONTH_OUTLINED, style=active_btn_style, expand=True)
    btn_hours = ft.ElevatedButton("Часы", icon=ft.Icons.ACCESS_TIME_OUTLINED, style=inactive_btn_style, expand=True)
    btn_settings = ft.ElevatedButton("Настройки", icon=ft.Icons.SETTINGS_OUTLINED, style=inactive_btn_style, expand=True)

    def set_tab(idx):
        shifts_view.visible = (idx == 0)
        hours_view.visible = (idx == 1)
        settings_view.visible = (idx == 2)

        btn_shifts.style = active_btn_style if idx == 0 else inactive_btn_style
        btn_hours.style = active_btn_style if idx == 1 else inactive_btn_style
        btn_settings.style = active_btn_style if idx == 2 else inactive_btn_style
        
        page.update()

    btn_shifts.on_click = lambda e: set_tab(0)
    btn_hours.on_click = lambda e: set_tab(1)
    btn_settings.on_click = lambda e: set_tab(2)

    tabs_row = ft.Row([btn_shifts, btn_hours, btn_settings], spacing=6)

    forms_card = ft.Card(
        elevation=2,
        content=ft.Container(
            content=ft.Column([
                shifts_view,
                hours_view,
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
        header,
        hero_card,
        tabs_row,
        forms_card,
        ft.Row([
            ft.ElevatedButton(
                "Рассчитать", 
                icon=ft.Icons.CALCULATE_OUTLINED, 
                on_click=calculate_click, 
                expand=True, 
                height=50,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=12),
                    bgcolor=ft.Colors.BLUE_600,
                    color=ft.Colors.WHITE
                )
            ),
            ft.OutlinedButton(
                "Очистить", 
                icon=ft.Icons.BACKSPACE_OUTLINED, 
                on_click=clear_click, 
                height=50,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))
            ),
        ], spacing=10),
        details_card
    )

if __name__ == "__main__":
    ft.app(target=main)

