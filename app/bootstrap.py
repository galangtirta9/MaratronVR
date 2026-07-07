"""Composition root: constructs every object with dependency injection.

All wiring happens here. MainWindow receives already-constructed
controllers and services so the window itself is just a shell.

This follows AGENTS.md: construction belongs in one place.
"""

from app.controllers.navigation_controller import NavigationController
from app.controllers.profile_controller import ProfileController
from app.core.profiles import load_data
from app.gui.main_window import MainWindow


def build_app():
    """Assemble the full application and return the MainWindow instance."""
    data = load_data()

    # Stub — window is built first so pages can inject back-references.
    window = MainWindow(data=data, profile_ctrl=None, nav=None)

    # Construct controllers with all dependencies visible.
    nav = NavigationController(
        content_stack=window.content_stack,
        tab_buttons=window.tab_buttons,
        settings_page=window.settings_page,
    )

    profile_ctrl = ProfileController(
        data=data,
        profile_combo=window.profile_combo,
        new_profile_button=window.new_profile_button,
        duplicate_profile_button=window.duplicate_profile_button,
        delete_profile_button=window.delete_profile_button,
        axis_combo=window.axis_combo,
        omnidirectional_check=window.omnidirectional_check,
        invert_check=window.invert_check,
        deadzone_spin=window.deadzone_spin,
        smoothing_spin=window.smoothing_spin,
        max_speed_spin=window.max_speed_spin,
        poll_spin=window.poll_spin,
        curve_editor=window.curve_editor,
        auto_sprint_check=window.auto_sprint_check,
        sprint_threshold_spin=window.sprint_threshold_spin,
        sprint_button_combo=window.sprint_button_combo,
        steamvr_sprint_button_combo=window.steamvr_sprint_button_combo,
        height_spin=window.height_spin,
        stride_estimate_label=window.stride_estimate_label,
        weight_spin=window.weight_spin,
        age_spin=window.age_spin,
        gender_combo=window.gender_combo,
        mouse_dpi_combo=window.mouse_dpi_combo,
        custom_dpi_spin=window.custom_dpi_spin,
        polling_rate_spin=window.polling_rate_spin,
        incline_spin=window.incline_spin,
        output_mode_combo=window.output_mode_combo,
        device_combo=window.device_combo,
        strava_client_id_edit=window.strava_client_id_edit,
        strava_client_secret_edit=window.strava_client_secret_edit,
        strava_status_label=window.strava_status_label,
        sensitivity_slider=window.sensitivity_slider,
        sensitivity_label=window.sensitivity_label,
        selected_profile_label=window.selected_profile_label,
        refresh_profiles_callback=window._refresh_profile_combo,
        load_profile_to_ui_callback=window._on_profile_loaded,
        render_tiles_callback=window._render_profile_tiles,
        update_header_callback=window._update_profile_header,
        show_toast_callback=window._toast,
        on_config_changed_callback=window._on_config_changed,
    )

    # Inject controllers into window.
    window.nav = nav
    window.profile_ctrl = profile_ctrl

    # Fix settings page save_callback now that profile_ctrl exists.
    window.settings_page.save_callback = profile_ctrl.save
    window.settings_page.sys_save_button.clicked.connect(profile_ctrl.save)

    # Wire signals and finalize.
    window._wire_signals()
    window._finalize_init()

    return window