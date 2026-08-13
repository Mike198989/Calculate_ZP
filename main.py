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
    page.padding = 15

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
        ("days_worked_normal", "Всего отработано смен", "0"),
        ("evening_shifts", "Количество вечерних смен", "0"),
        ("days_pre_holiday_reduced", "Сокращенные дни (общее)", "0"),
        ("days_pre_holiday_reduced_evening", "Сокращенные вечерние смены", "0"),
        ("hours_overtime_first_two", "Переработка (первые 2ч)", "0"),
        ("hours_overtime_after_two", "Переработка (последующие)", "0"),
        ("hours_weekend_holiday", "Часы в выходные/праздники", "0"),
        ("days_non_working_holiday", "Нерабочие праздничные дни", "0"),
        ("hours_night", "Ночные часы", "0"),
    ]

    saved_inputs = {}
    if os.path.exists(last_input_file):
        try:
            with open(last_input_file, "r", encoding="utf-8") as f:
                saved_inputs = json.load(f)
        except Exception:
            pass

    for key, label, default_val in fields_config:
        val = saved_inputs.get(key, default_val)
        inputs[key] = ft.TextField(
            label=label,
            value=str(val if val is not None else default_val),
            keyboard_type=ft.KeyboardType.NUMBER,
            height=55,
        )

    theme_dropdown = ft.Dropdown(
        label="Тема оформления",
        value=saved_theme,
        options=[
            ft.dropdown.Option("system", "Системная"),
            ft.dropdown.Option("dark", "Темная"),
            ft.dropdown.Option("light", "Светлая"),
        ],
    )

    settings_inputs = {}
    coefficients_config = [
        ("hourly_rate", "Часовая ставка (руб.)"),
        ("overtime_multiplier_first_two_hours", "Множитель сверхурочных (1-2 ч)"),
        ("overtime_multiplier_after_two_hours", "Множитель сверхурочных (после 2 ч)"),
        ("weekend_holiday_multiplier", "Множитель вых./праздников (часы)"),
        ("non_working_holiday_multiplier", "Множитель праздничных дней"),
        ("night_surcharge_percent", "Доплата за ночь (доля, напр. 0.2)"),
        ("evening_surcharge_percent", "Доплата за вечер (доля, напр. 0.2)"),
        ("hazard_surcharge_percent", "Вредность (доля, напр. 0.12)"),
        ("difficulty_surcharge_percent", "Сложность (доля, напр. 0.1)"),
        ("ndfl_rate", "НДФЛ (доля, напр. 0.13)"),
        ("bonus_percent_of_base_hours", "Премия от базы (доля, напр. 0.95)"),
    ]

    for k, label in coefficients_config:
        val = coefficients.get(k, 0)
        settings_inputs[k] = ft.TextField(
            label=label,
            value=str(val),
            keyboard_type=ft.KeyboardType.NUMBER,
            height=55,
        )

    net_output = ft.Text("0.00 руб.", size=28, weight=ft.FontWeight.BOLD)
    details_column = ft.Column()

    def show_snack(text):
        sb = ft.SnackBar(ft.Text(text))
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
            details_column.controls.clear()

            for name, val in result["breakdown"].items():
                details_column.controls.append(
                    ft.Row(
                        [
                            ft.Text(name, size=14, expand=True),
                            ft.Text(f"{val:,.2f}", size=14, weight=ft.FontWeight.BOLD)
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
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
        details_column.controls.clear()
        save_state()
        page.update()

    shifts_view = ft.Column([
        inputs["days_worked_normal"],
        inputs["evening_shifts"],
    ], spacing=15, visible=True)

    hours_view = ft.Column([
        inputs["days_pre_holiday_reduced"],
        inputs["days_pre_holiday_reduced_evening"],
        inputs["hours_overtime_first_two"],
        inputs["hours_overtime_after_two"],
        inputs["hours_weekend_holiday"],
        inputs["days_non_working_holiday"],
        inputs["hours_night"],
    ], spacing=15, visible=False)

    settings_view = ft.Column([
        theme_dropdown,
        ft.Divider(),
        *[tf for tf in settings_inputs.values()],
        ft.ElevatedButton("Сохранить настройки", on_click=save_settings_click, height=45)
    ], spacing=15, visible=False)

    def show_shifts(e):
        shifts_view.visible = True
        hours_view.visible = False
        settings_view.visible = False
        page.update()

    def show_hours(e):
        shifts_view.visible = False
        hours_view.visible = True
        settings_view.visible = False
        page.update()

    def show_settings_tab(e):
        shifts_view.visible = False
        hours_view.visible = False
        settings_view.visible = True
        page.update()

    tab_btn_shifts = ft.TextButton("Смены", on_click=show_shifts, expand=True)
    tab_btn_hours = ft.TextButton("Часы / Перераб.", on_click=show_hours, expand=True)
    tab_btn_settings = ft.TextButton("Настройки", on_click=show_settings_tab, expand=True)

    custom_tabs_ui = ft.Column([
        ft.Row([tab_btn_shifts, tab_btn_hours, tab_btn_settings], alignment=ft.MainAxisAlignment.CENTER, spacing=0),
        ft.Divider(height=1),
        ft.Container(content=shifts_view, padding=10),
        ft.Container(content=hours_view, padding=10),
        ft.Container(content=settings_view, padding=10)
    ])

    # Безопасное выравнивание заголовка по центру с версткой через Row
    header = ft.Container(
        content=ft.Row(
            [
                ft.Text(
                    "Калькулятор ЗП", 
                    size=24, 
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER
        ),
        padding=ft.padding.only(top=20, bottom=10)
    )

    page.add(
        header,
        custom_tabs_ui,
        ft.Row([
            ft.ElevatedButton("Рассчитать", on_click=calculate_click, expand=True, height=50),
            ft.OutlinedButton("Очистить", on_click=clear_click, height=50),
        ], spacing=10),
        ft.Divider(),
        ft.Text("Результат:", size=16, weight=ft.FontWeight.BOLD),
        net_output,
        ft.Divider(),
        ft.Text("Детализация:", size=16, weight=ft.FontWeight.BOLD),
        details_column
    )

if __name__ == "__main__":
    ft.app(target=main)

