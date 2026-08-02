from scripts.setup import plan_setup


def test_missing_ollama_yields_install_instructions_not_an_auto_install():
    # An OS-level install must never happen without the user running it themselves.
    plan = plan_setup(ollama_running=False, installed_models=[], platform="win32")

    assert plan.action == "instruct"
    assert "ollama.com" in plan.message


def test_running_ollama_without_the_model_yields_a_pull():
    plan = plan_setup(ollama_running=True, installed_models=[], platform="win32")

    assert plan.action == "pull"
    assert plan.model


def test_everything_present_is_a_no_op():
    plan = plan_setup(
        ollama_running=True, installed_models=["qwen2.5:7b-instruct"], platform="linux"
    )

    assert plan.action == "ok"


def test_a_quantised_variant_counts_as_installed():
    # The local tag carries a -q4_K_M suffix; matching only the plain tag would
    # trigger a needless 4.7 GB download.
    plan = plan_setup(
        ollama_running=True,
        installed_models=["qwen2.5:7b-instruct-q4_K_M"],
        platform="win32",
    )

    assert plan.action == "ok"


def test_instructions_are_platform_specific():
    windows = plan_setup(ollama_running=False, installed_models=[], platform="win32")
    linux = plan_setup(ollama_running=False, installed_models=[], platform="linux")

    assert windows.message != linux.message
