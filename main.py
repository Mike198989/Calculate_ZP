import flet as ft
import json
import os

# --- Значения коэффициентов по умолчанию ---
DEFAULT_COEFFICIENTS = {
    "hourly_rate": 250.0,
    "night_allowance_pct": 20.0,
    "overtime_first_2h_pct": 50.0,
    "overtime_after_2h_pct": 100.0,
    "holiday_work_pct": 100.0,
    "ndfl_pct": 13.0,
    "advance_pct": 50.0,
    "monthly_base_salary": 50000.0,
    "monthly_norm_hours": 160.0,
}


def format_rub(val: float) -> str:
    """Форматирует число в строку с денежным представлением (например: 12 345,67 ₽)."""
    r_val = round(val, 2)
    if r_val == 0:
        return "0,00 ₽"
    sign = "-" if r_val < 0 else ""
    val_abs = abs(r_val)
    s = f"{val_abs:,.2f}".replace(",", " ").replace(".", ",")
    return f"{sign}{s} ₽"


def main(page: ft.Page):
    page.title = "Калькулятор Зарплаты"
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 16

    # --- Состояние программы ---
    coefficients = DEFAULT_COEFFICIENTS.copy()
    saved_inputs = {}
    last_calc_result = {}
    history = []
    current_mode = "shifts"  # "shifts" или "oklad"

    # Хранилище ссылок на поля ввода
    inputs = {}
    steppers_dict = {}
    settings_inputs = {}

    # --- Загрузка и сохранение данных ---
    def get_storage_file_path():
        try:
            return os.path.join(page.client_storage_dir, "calc_zp_data.json")
        except Exception:
            return "calc_zp_data.json"

    def load_state():
        nonlocal coefficients, saved_inputs, history
        file_path = get_storage_file_path()
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    coefficients.update(data.get("coefficients", {}))
                    saved_inputs = data.get("inputs", {})
                    history = data.get("history", [])
            except Exception:
                pass

    def save_state():
        file_path = get_storage_file_path()
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "coefficients": coefficients,
                        "inputs": saved_inputs,
                        "history": history,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception:
            pass

    load_state()

    # --- Функция уведомлений (SnackBar) ---
    def show_snack(text: str):
        sb = ft.SnackBar(content=ft.Text(text))
        try:
            page.open(sb)
        except Exception:
            page.snack_bar = sb
            sb.open = True
            page.update()

    # --- Ядро расчёта зарплаты ---
    def compute_salary(mode: str) -> dict:
        def get_val(key: str, default: float = 0.0) -> float:
            if key in inputs:
                try:
                    val = float(inputs[key].value.replace(",", "."))
                    saved_inputs[key] = inputs[key].value
                    return val
                except ValueError:
                    return default
            return saved_inputs.get(key, default)

        rate = coefficients.get("hourly_rate", 250.0)
        night_pct = coefficients.get("night_allowance_pct", 20.0) / 100.0
        overtime_1_pct = coefficients.get("overtime_first_2h_pct", 50.0) / 100.0
        overtime_2_pct = coefficients.get("overtime_after_2h_pct", 100.0) / 100.0
        holiday_pct = coefficients.get("holiday_work_pct", 100.0) / 100.0
        ndfl_pct = coefficients.get("ndfl_pct", 13.0) / 100.0
        advance_pct = coefficients.get("advance_pct", 50.0) / 100.0

        if mode == "shifts":
            hours_day = get_val("hours_day", 0.0)
            hours_night = get_val("hours_night", 0.0)
            overtime_first_2h = get_val("overtime_first_2h", 0.0)
            overtime_after_2h = get_val("overtime_after_2h", 0.0)
            hours_holiday = get_val("hours_holiday", 0.0)
            bonus = get_val("bonus", 0.0)
            deductions = get_val("deductions", 0.0)

            total_hours = hours_day + hours_night
            base_pay = total_hours * rate
            night_pay = hours_night * rate * night_pct
            overtime_pay = (overtime_first_2h * rate * (1 + overtime_1_pct)) + (
                overtime_after_2h * rate * (1 + overtime_2_pct)
            )
            holiday_pay = hours_holiday * rate * (1 + holiday_pct)

            gross = base_pay + night_pay + overtime_pay + holiday_pay + bonus
            ndfl = gross * ndfl_pct
            net = gross - ndfl - deductions
            advance = net * advance_pct
            final_payout = net - advance

            return {
                "mode": "shifts",
                "total_hours": total_hours,
                "base_pay": base_pay,
                "night_pay": night_pay,
                "overtime_pay": overtime_pay,
                "holiday_pay": holiday_pay,
                "bonus": bonus,
                "deductions": deductions,
                "gross": gross,
                "ndfl": ndfl,
                "net": net,
                "advance": advance,
                "final_payout": final_payout,
            }
        else:  # oklad
            base_salary = get_val(
                "monthly_base_salary",
                coefficients.get("monthly_base_salary", 50000.0),
            )
            norm_hours = get_val(
                "monthly_norm_hours",
                coefficients.get("monthly_norm_hours", 160.0),
            )
            worked_hours = get_val("worked_hours", norm_hours)
            hours_night = get_val("hours_night_oklad", 0.0)
            overtime_first_2h = get_val("overtime_first_2h_oklad", 0.0)
            overtime_after_2h = get_val("overtime_after_2h_oklad", 0.0)
            hours_holiday = get_val("hours_holiday_oklad", 0.0)
            bonus = get_val("bonus_oklad", 0.0)
            deductions = get_val("deductions_oklad", 0.0)

            eff_rate = base_salary / norm_hours if norm_hours > 0 else 0.0

            base_pay = worked_hours * eff_rate
            night_pay = hours_night * eff_rate * night_pct
            overtime_pay = (overtime_first_2h * eff_rate * (1 + overtime_1_pct)) + (
                overtime_after_2h * eff_rate * (1 + overtime_2_pct)
            )
            holiday_pay = hours_holiday * eff_rate * (1 + holiday_pct)

            gross = base_pay + night_pay + overtime_pay + holiday_pay + bonus
            ndfl = gross * ndfl_pct
            net = gross - ndfl - deductions
            advance = net * advance_pct
            final_payout = net - advance

            return {
                "mode": "oklad",
                "eff_rate": eff_rate,
                "base_pay": base_pay,
                "night_pay": night_pay,
                "overtime_pay": overtime_pay,
                "holiday_pay": holiday_pay,
                "bonus": bonus,
                "deductions": deductions,
                "gross": gross,
                "ndfl": ndfl,
                "net": net,
                "advance": advance,
                "final_payout": final_payout,
            }

    # --- Элементы отображения результатов ---
    net_output = ft.Text(
        "0,00 ₽", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400
    )
    payout_output = ft.Text("Остаток к выплате: 0,00 ₽", size=14, color=ft.Colors.GREY_400)
    details_column = ft.Column(spacing=6)

    def auto_recalculate(e=None):
        nonlocal last_calc_result
        last_calc_result = compute_salary(current_mode)
        net_output.value = format_rub(last_calc_result["net"])
        payout_output.value = f"Остаток к выплате (после аванса): {format_rub(last_calc_result['final_payout'])}"

        details_column.controls.clear()
        details_items = [
            ("Начислено всего (Gross)", last_calc_result["gross"], True),
            ("Основная оплата / Оклад", last_calc_result["base_pay"], False),
            ("Ночная доплата", last_calc_result["night_pay"], False),
            ("Сверхурочные (первые 2 ч)", last_calc_result["overtime_pay"], False),
            ("Праздничные / Выходные", last_calc_result["holiday_pay"], False),
            ("Премия / Надбавка", last_calc_result["bonus"], False),
            ("НДФЛ (13%)", -last_calc_result["ndfl"], False),
            ("Удержания", -last_calc_result["deductions"], False),
            ("Расчётный аванс (50%)", last_calc_result["advance"], False),
        ]

        for label, val, is_bold in details_items:
            color = ft.Colors.RED_300 if val < 0 else (ft.Colors.BLUE_200 if is_bold else ft.Colors.WHITE70)
            details_column.controls.append(
                ft.Row(
                    controls=[
                        ft.Text(label, size=13, weight=ft.FontWeight.BOLD if is_bold else ft.FontWeight.NORMAL),
                        ft.Text(
                            format_rub(val),
                            size=13,
                            weight=ft.FontWeight.BOLD if is_bold else ft.FontWeight.NORMAL,
                            color=color,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )

        save_state()
        page.update()

    # --- Вспомогательная функция для создания полей с кнопками -/+ ---
    def create_stepper_field(key: str, label: str, default_val: str, step: float = 1.0):
        val_str = saved_inputs.get(key, default_val)
        tf = ft.TextField(
            value=val_str,
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
            dense=True,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
            on_change=auto_recalculate,
        )
        inputs[key] = tf

        def change_val(delta: float):
            try:
                curr = float(tf.value.replace(",", "."))
            except ValueError:
                curr = 0.0
            new_val = max(0.0, curr + delta)
            tf.value = f"{new_val:g}"
            auto_recalculate()

        btn_minus = ft.IconButton(
            icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
            icon_color=ft.Colors.RED_400,
            on_click=lambda _: change_val(-step),
        )
        btn_plus = ft.IconButton(
            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
            icon_color=ft.Colors.GREEN_400,
            on_click=lambda _: change_val(step),
        )

        row = ft.Row(
            controls=[
                ft.Text(label, expand=True, size=14),
                btn_minus,
                ft.Container(content=tf, width=80),
                btn_plus,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        steppers_dict[key] = row
        return row

    # --- Поля для вкладки "По сменам" ---
    shifts_tab_content = ft.Column(
        controls=[
            ft.Text("Параметры смен", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_300),
            create_stepper_field("hours_day", "Дневные часы", "120", 8.0),
            create_stepper_field("hours_night", "Ночные часы", "40", 4.0),
            create_stepper_field("overtime_first_2h", "Сверхурочные (до 2 ч)", "0", 1.0),
            create_stepper_field("overtime_after_2h", "Сверхурочные (свыше 2 ч)", "0", 1.0),
            create_stepper_field("hours_holiday", "Праздничные/Выходные ч.", "0", 8.0),
            create_stepper_field("bonus", "Премии / Премиальные (₽)", "0", 1000.0),
            create_stepper_field("deductions", "Удержания / Штрафы (₽)", "0", 500.0),
        ],
        spacing=10,
    )

    # --- Поля для вкладки "Оклад" ---
    oklad_tab_content = ft.Column(
        controls=[
            ft.Text("Параметры оклада", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_300),
            create_stepper_field("monthly_base_salary", "Месячный оклад (₽)", "50000", 5000.0),
            create_stepper_field("monthly_norm_hours", "Норма часов в месяце", "160", 8.0),
            create_stepper_field("worked_hours", "Отработано часов по норме", "160", 8.0),
            create_stepper_field("hours_night_oklad", "Ночные часы", "0", 4.0),
            create_stepper_field("overtime_first_2h_oklad", "Сверхурочные (до 2 ч)", "0", 1.0),
            create_stepper_field("overtime_after_2h_oklad", "Сверхурочные (свыше 2 ч)", "0", 1.0),
            create_stepper_field("hours_holiday_oklad", "Праздничные/Выходные ч.", "0", 8.0),
            create_stepper_field("bonus_oklad", "Премия (₽)", "0", 1000.0),
            create_stepper_field("deductions_oklad", "Удержания (₽)", "0", 500.0),
        ],
        spacing=10,
    )

    # --- Вкладка "Настройки & Коэффициенты" ---
    def create_setting_field(key: str, label: str):
        val = str(coefficients.get(key, DEFAULT_COEFFICIENTS[key]))
        tf = ft.TextField(
            label=label,
            value=val,
            keyboard_type=ft.KeyboardType.NUMBER,
            dense=True,
        )
        settings_inputs[key] = tf
        return tf

    def save_settings(e):
        for k, tf in settings_inputs.items():
            try:
                coefficients[k] = float(tf.value.replace(",", "."))
            except ValueError:
                pass
        save_state()
        show_snack("Настройки успешно сохранены!")
        auto_recalculate()

    def reset_settings(e):
        nonlocal coefficients
        coefficients = DEFAULT_COEFFICIENTS.copy()
        for k, tf in settings_inputs.items():
            tf.value = str(coefficients[k])
        save_state()
        show_snack("Настройки сброшены к значениям по умолчанию.")
        auto_recalculate()

    settings_tab_content = ft.Column(
        controls=[
            ft.Text("Ставки и коэффициенты", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_300),
            create_setting_field("hourly_rate", "Базовая часовая ставка (₽/ч)"),
            create_setting_field("night_allowance_pct", "Надбавка за ночные часы (%)"),
            create_setting_field("overtime_first_2h_pct", "Сверхурочные: первые 2 ч (%)"),
            create_setting_field("overtime_after_2h_pct", "Сверхурочные: последующие ч (%)"),
            create_setting_field("holiday_work_pct", "Оплата праздничных/выходных (%)"),
            create_setting_field("ndfl_pct", "Ставка НДФЛ (%)"),
            create_setting_field("advance_pct", "Размер аванса (%)"),
            ft.Row(
                controls=[
                    ft.ElevatedButton(
                        "Сохранить настройки",
                        icon=ft.Icons.SAVE,
                        on_click=save_settings,
                        style=ft.ButtonStyle(color=ft.Colors.GREEN_400),
                    ),
                    ft.OutlinedButton(
                        "Сбросить",
                        icon=ft.Icons.RESTORE,
                        on_click=reset_settings,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        ],
        spacing=12,
    )

    # --- Вкладка "История" ---
    history_list_view = ft.Column(spacing=8)

    def update_history_view():
        history_list_view.controls.clear()
        if not history:
            history_list_view.controls.append(
                ft.Text("История расчётов пуста", color=ft.Colors.GREY_500, italic=True)
            )
            page.update()
            return

        for idx, item in enumerate(reversed(history)):
            real_idx = len(history) - 1 - idx
            mode_title = "Смены" if item.get("mode") == "shifts" else "Оклад"
            net_val = format_rub(item.get("net", 0.0))

            def delete_item(e, i=real_idx):
                history.pop(i)
                save_state()
                update_history_view()
                show_snack("Запись удалена из истории")

            history_list_view.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Column(
                                    controls=[
                                        ft.Text(f"{mode_title} — {net_val}", weight=ft.FontWeight.BOLD, size=15),
                                        ft.Text(f"Gross: {format_rub(item.get('gross', 0.0))}", size=12, color=ft.Colors.GREY_400),
                                    ],
                                    spacing=2,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_color=ft.Colors.RED_300,
                                    on_click=delete_item,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=10,
                    )
                )
            )
        page.update()

    def save_to_history(e):
        if last_calc_result:
            history.append(last_calc_result.copy())
            if len(history) > 50:
                history.pop(0)
            save_state()
            update_history_view()
            show_snack("Расчёт сохранён в историю!")

    def clear_history(e):
        history.clear()
        save_state()
        update_history_view()
        show_snack("История очищена.")

    history_tab_content = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text("История сохранённых расчётов", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_300),
                    ft.TextButton("Очистить всё", on_click=clear_history),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            history_list_view,
        ],
        spacing=10,
    )

    # --- Переключатель режимов (ВАЖНО: используется list ["shifts"], а не set) ---
    def on_tab_change(e):
        nonlocal current_mode
        sel = e.control.selected
        if isinstance(sel, (list, set, tuple)) and len(sel) > 0:
            tab_key = list(sel)[0]
        else:
            tab_key = "shifts"

        current_mode = tab_key
        # Принудительно передаём список, чтобы Flet не пытался сериализовать set
        tab_segmented.selected = [tab_key]

        if tab_key == "shifts":
            main_content_container.content = shifts_tab_content
        elif tab_key == "oklad":
            main_content_container.content = oklad_tab_content
        elif tab_key == "settings":
            main_content_container.content = settings_tab_content
        elif tab_key == "history":
            update_history_view()
            main_content_container.content = history_tab_content

        auto_recalculate()

    # ЗДЕСЬ ИСПРАВЛЕНИЕ: selected задаётся списком ["shifts"], а не множеством {"shifts"}
    tab_segmented = ft.SegmentedButton(
        selected=["shifts"],
        segments=[
            ft.Segment(value="shifts", label=ft.Text("Смены"), icon=ft.Icon(ft.Icons.SCHEDULE)),
            ft.Segment(value="oklad", label=ft.Text("Оклад"), icon=ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET)),
            ft.Segment(value="settings", label=ft.Text("Опции"), icon=ft.Icon(ft.Icons.SETTINGS)),
            ft.Segment(value="history", label=ft.Text("История"), icon=ft.Icon(ft.Icons.HISTORY)),
        ],
        on_change=on_tab_change,
    )

    main_content_container = ft.Container(content=shifts_tab_content, padding=ft.padding.only(top=10))

    # --- Вывод итога (Главный экран результатов) ---
    results_card = ft.Card(
        color=ft.Colors.SURFACE_VARIANT,
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("На руки (Net):", size=14, color=ft.Colors.GREY_300),
                    net_output,
                    payout_output,
                    ft.Divider(height=10, color=ft.Colors.WHITE24),
                    details_column,
                    ft.Row(
                        controls=[
                            ft.ElevatedButton(
                                "Сохранить в историю",
                                icon=ft.Icons.BOOKMARK_ADD,
                                on_click=save_to_history,
                                expand=True,
                            ),
                        ],
                    ),
                ],
                spacing=8,
            ),
            padding=14,
        ),
    )

    # --- Сборка главной страницы ---
    page.add(
        ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("🧮 Калькулятор ЗП", size=20, weight=ft.FontWeight.BOLD),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                tab_segmented,
                main_content_container,
                ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                results_card,
            ],
            spacing=10,
        )
    )

    # Первоначальный расчёт после загрузки компонентов
    auto_recalculate()


if __name__ == "__main__":
    ft.app(target=main)

