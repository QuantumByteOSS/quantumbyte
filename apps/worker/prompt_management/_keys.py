"""
Central registry of every prompt name.

Every ``get_prompt_text`` call MUST use a key from this enum — no raw strings.

Naming convention:
    Member name  = prompt path uppercased with ``/`` replaced by ``__``.
    Member value = the prompt path itself (relative to ``shared/prompts``).

Example::

    AGENTS__MAIN_AGENT__SYSTEM_PROMPT = "agents/main_agent/system_prompt"

The tree under ``shared/prompts/`` is the source of truth for every member;
``fetch_and_cache`` loads ``<value>.md`` for each key at boot.

Usage::

    from submodule.prompt_management import PromptKey as PK, get_prompt_text

    get_prompt_text(PK.AGENTS__MAIN_AGENT__USER_QUERY_WITH_CONTEXT_FORMAT, conversation_id=...)
"""

from enum import StrEnum


class PromptKey(StrEnum):
    """Every prompt name in use across the system."""

    # ── PARTNER (main agent) root ────────────────────────────────────────
    AGENTS__MAIN_AGENT__SYSTEM_PROMPT = "agents/main_agent/system_prompt"
    AGENTS__MAIN_AGENT__USER_QUERY_WITH_CONTEXT_FORMAT = "agents/main_agent/user_query_with_context_format"

    # ── PARTNER tools (mcp_partner) ──────────────────────────────────────
    AGENTS__MAIN_AGENT__TOOLS__ABOUT_YOU_AS_AI_AGENT__DESCRIPTION = "agents/main_agent/tools/about_you_as_ai_agent/description"
    AGENTS__MAIN_AGENT__TOOLS__CONGRATULATE__DESCRIPTION = "agents/main_agent/tools/congratulate/description"
    AGENTS__MAIN_AGENT__TOOLS__GET_DECK_INFO__DESCRIPTION = "agents/main_agent/tools/get_deck_info/description"
    AGENTS__MAIN_AGENT__TOOLS__GET_USER_SUBSCRIPTION_INFORMATION__DESCRIPTION = "agents/main_agent/tools/get_user_subscription_information/description"
    AGENTS__MAIN_AGENT__TOOLS__GIVE_GIVEAWAY_CREDIT__DESCRIPTION = "agents/main_agent/tools/give_giveaway_credit/description"
    AGENTS__MAIN_AGENT__TOOLS__HIGHLIGHT_AND_TOOLTIP__DESCRIPTION = "agents/main_agent/tools/highlight_and_tooltip/description"
    AGENTS__MAIN_AGENT__TOOLS__INTRODUCE_AGENT__DESCRIPTION = "agents/main_agent/tools/introduce_agent/description"
    AGENTS__MAIN_AGENT__TOOLS__PLATFORM_ELEMENTS__DESCRIPTION = "agents/main_agent/tools/platform_elements/description"
    AGENTS__MAIN_AGENT__TOOLS__TRIGGER_PAYWALL__DESCRIPTION = "agents/main_agent/tools/trigger_paywall/description"
    AGENTS__MAIN_AGENT__TOOLS__UPGRADE_ACCOUNT_INFORMATION__DESCRIPTION = "agents/main_agent/tools/upgrade_account_information/description"
    AGENTS__MAIN_AGENT__TOOLS__USER_INTERESTED_IN_THEIR_APP__DESCRIPTION = "agents/main_agent/tools/user_interested_in_their_app/description"

    # ── PARTNER goal-system tools ────────────────────────────────────────
    AGENTS__MAIN_AGENT__TOOLS__GOAL_TOOLS__ADD_GOAL_DEPENDENCY__DESCRIPTION = "agents/main_agent/tools/goal_tools/add_goal_dependency/description"
    AGENTS__MAIN_AGENT__TOOLS__GOAL_TOOLS__CREATE_GOAL__DESCRIPTION = "agents/main_agent/tools/goal_tools/create_goal/description"
    AGENTS__MAIN_AGENT__TOOLS__GOAL_TOOLS__DETAIL_GOAL__DESCRIPTION = "agents/main_agent/tools/goal_tools/detail_goal/description"
    AGENTS__MAIN_AGENT__TOOLS__GOAL_TOOLS__GET_AVAILABLE_GOALS__DESCRIPTION = "agents/main_agent/tools/goal_tools/get_available_goals/description"
    AGENTS__MAIN_AGENT__TOOLS__GOAL_TOOLS__GET_DETAIL_GOAL__DESCRIPTION = "agents/main_agent/tools/goal_tools/get_detail_goal/description"
    AGENTS__MAIN_AGENT__TOOLS__GOAL_TOOLS__SUBMIT_GOAL_FORM__DESCRIPTION = "agents/main_agent/tools/goal_tools/submit_goal_form/description"
    AGENTS__MAIN_AGENT__TOOLS__GOAL_TOOLS__SWITCH_FOCUS_GOAL__DESCRIPTION = "agents/main_agent/tools/goal_tools/switch_focus_goal/description"
    AGENTS__MAIN_AGENT__TOOLS__GOAL_TOOLS__UPDATE_GOAL_STATUS__DESCRIPTION = "agents/main_agent/tools/goal_tools/update_goal_status/description"

    # ── PARTNER proposal-goals tools ─────────────────────────────────────
    AGENTS__MAIN_AGENT__TOOLS__PROPOSAL_GOALS__CREATE__DESCRIPTION = "agents/main_agent/tools/proposal_goals/create/description"
    AGENTS__MAIN_AGENT__TOOLS__PROPOSAL_GOALS__GET__DESCRIPTION = "agents/main_agent/tools/proposal_goals/get/description"
    AGENTS__MAIN_AGENT__TOOLS__PROPOSAL_GOALS__UPDATE__DESCRIPTION = "agents/main_agent/tools/proposal_goals/update/description"
    AGENTS__MAIN_AGENT__TOOLS__PROPOSAL_GOALS__DELETE__DESCRIPTION = "agents/main_agent/tools/proposal_goals/delete/description"

    # ── DESIGNER subagent + tools ────────────────────────────────────────
    AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__DESCRIPTION = "agents/main_agent/subagents/designer_agent/description"
    AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__SYSTEM_PROMPT = "agents/main_agent/subagents/designer_agent/system_prompt"
    AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__TOOLS__DELETE_ASSET__DESCRIPTION = (
        "agents/main_agent/subagents/designer_agent/tools/delete_asset/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__TOOLS__GENERATE_PRODUCT_LOGO__DESCRIPTION = (
        "agents/main_agent/subagents/designer_agent/tools/generate_product_logo/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__TOOLS__IMAGES_SEARCH__DESCRIPTION = (
        "agents/main_agent/subagents/designer_agent/tools/images_search/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__TOOLS__GET_ASSET_URL__DESCRIPTION = (
        "agents/main_agent/subagents/designer_agent/tools/get_asset_url/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__TOOLS__LIST_ASSETS__DESCRIPTION = "agents/main_agent/subagents/designer_agent/tools/list_assets/description"
    AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__TOOLS__UPDATE_PRODUCT_DESCRIPTION__DESCRIPTION = (
        "agents/main_agent/subagents/designer_agent/tools/update_product_description/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__TOOLS__UPDATE_PRODUCT_LOGO__DESCRIPTION = (
        "agents/main_agent/subagents/designer_agent/tools/update_product_logo/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__TOOLS__UPDATE_PRODUCT_TITLE__DESCRIPTION = (
        "agents/main_agent/subagents/designer_agent/tools/update_product_title/description"
    )

    # ── ENGINEER subagent + tools ────────────────────────────────────────
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__DESCRIPTION = "agents/main_agent/subagents/engineer_agent/description"
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__SYSTEM_PROMPT = "agents/main_agent/subagents/engineer_agent/system_prompt"
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__COMPLETE_AI_TASK__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/complete_ai_task/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__COMPLETE_AI_TASK__RETURN_DIRECTIVE__FAILURE = (
        "agents/main_agent/subagents/engineer_agent/tools/complete_ai_task/return_directive/failure"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__COMPLETE_AI_TASK__RETURN_DIRECTIVE__SUCCESS = (
        "agents/main_agent/subagents/engineer_agent/tools/complete_ai_task/return_directive/success"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__COMPLETE_INITIAL_GENERATION__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/complete_initial_generation/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__COMPLETE_INITIAL_GENERATION__RETURN_DIRECTIVE__FAILURE = (
        "agents/main_agent/subagents/engineer_agent/tools/complete_initial_generation/return_directive/failure"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__COMPLETE_INITIAL_GENERATION__RETURN_DIRECTIVE__SUCCESS = (
        "agents/main_agent/subagents/engineer_agent/tools/complete_initial_generation/return_directive/success"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__DELETE_ENVIRONMENT_VARIABLE__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/delete_environment_variable/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__EXECUTE_AI_TASK__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/execute_ai_task/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__EXECUTE_AI_TASK__RETURN_DIRECTIVE__BUILD_IT = (
        "agents/main_agent/subagents/engineer_agent/tools/execute_ai_task/return_directive/build_it"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__EXECUTE_AI_TASK__RETURN_DIRECTIVE__REGULAR = (
        "agents/main_agent/subagents/engineer_agent/tools/execute_ai_task/return_directive/regular"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__GET_CURRENT_APP_CONFIG__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/get_current_app_config/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__GET_ENVIRONMENT_VARIABLE__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/get_environment_variable/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__INJECT_SCAFFOLD__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/inject_scaffold/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__LIST_ENVIRONMENT_VARIABLES__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/list_environment_variables/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__SEARCH_SCAFFOLDS__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/search_scaffolds/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__SET_ENVIRONMENT_VARIABLE__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/set_environment_variable/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__TRIGGER_INITIAL_GENERATION__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/trigger_initial_generation/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__TRIGGER_INITIAL_GENERATION__RETURN_DIRECTIVE_TEMPLATE = (
        "agents/main_agent/subagents/engineer_agent/tools/trigger_initial_generation/return_directive_template"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__UPDATE_APP_CONFIG__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/update_app_config/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__FORCE_SYNC_CODE_WITH_APP_PREVIEW__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/force_sync_code_with_app_preview/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__RELOAD_APP_PREVIEW__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/reload_app_preview/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__GET_APP_PREVIEW_STATUS__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/get_app_preview_status/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__GET_APP_PREVIEW_LOGS__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/get_app_preview_logs/description"
    )
    AGENTS__MAIN_AGENT__SUBAGENTS__ENGINEER_AGENT__TOOLS__APP_RUNTIME_CHECKER__DESCRIPTION = (
        "agents/main_agent/subagents/engineer_agent/tools/app_runtime_checker/description"
    )

    # ── STRATEGIST persona (used by the deterministic product-overview
    # reconcile pass in main.py — not a Task-target subagent) ─────────────
    AGENTS__MAIN_AGENT__SUBAGENTS__STRATEGIST_AGENT__SYSTEM_PROMPT = "agents/main_agent/subagents/strategist_agent/system_prompt"

    # ── RECONCILE MIDDLE EDITOR ENGINEER AGENT ───────────────────────────
    AGENTS__RECONCILE_MIDDLE_EDITOR_ENGINEER_AGENT__SYSTEM_PROMPT = "agents/reconcile_middle_editor_engineer_agent/system_prompt"
    AGENTS__RECONCILE_MIDDLE_EDITOR_ENGINEER_AGENT__USER_QUERY = "agents/reconcile_middle_editor_engineer_agent/user_query"

    # ── MISC service prompts (initial-generation trigger) ────────────────

    MISC__USER_QUERY = "misc/user_query"

    # ── MIDDLE EDITOR service prompts ────────────────────────────────────
    MIDDLE_EDITOR__DESC_SYSTEM = "middle_editor/desc_system"
    MIDDLE_EDITOR__DESC_MAIN = "middle_editor/desc_main"
    MIDDLE_EDITOR__SCHEMA_SYSTEM = "middle_editor/schema_system"
    MIDDLE_EDITOR__SCHEMA_MAIN = "middle_editor/schema_main"
    MIDDLE_EDITOR__FRONTEND_DESIGN = "middle_editor/frontend_design"
    MIDDLE_EDITOR__MAIN_PROMPT = "middle_editor/main_prompt"
    MIDDLE_EDITOR__SYSTEM_PROMPT = "middle_editor/system_prompt"

    # ── USER SLIDES (free-trial blueprint generation) ────────────────────
    # The agent-path slide prompts were retired when blueprints moved to workspace
    # files authored by the agent (see the creative-blueprints skill). Only the
    # free-trial generator's two prompts remain.
    USER_SLIDES__SLIDE_GENERATION_SYSTEM_PROMPT = "user_slides/slide_generation_system_prompt"
    USER_SLIDES__FREE_TRIAL_DEFAULT_SLIDES_PROMPT = "user_slides/free_trial_default_slides_prompt"
