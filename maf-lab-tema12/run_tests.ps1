param(
    [switch]$Online,
    [switch]$CompareModels,
    [switch]$NoDrift,
    [switch]$RequireBaseline
)

if ($Online) {
    $env:RUN_LLM_TESTS = "1"
}
else {
    $env:RUN_LLM_TESTS = "0"
}

if ($CompareModels) {
    $env:RUN_MODEL_COMPARISON = "1"
}
else {
    $env:RUN_MODEL_COMPARISON = "0"
}

if ($NoDrift) {
    $env:RUN_DRIFT_CHECK = "0"
}
else {
    $env:RUN_DRIFT_CHECK = "1"
}

if ($RequireBaseline) {
    $env:REQUIRE_BASELINE = "1"
}
else {
    $env:REQUIRE_BASELINE = "0"
}

python run_test_suite.py

exit $LASTEXITCODE