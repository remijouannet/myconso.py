#!/usr/bin/env bash
set -xeuo pipefail

# Ensure required environment variables are set
: "${MYCONSO_EMAIL:?Missing environment variable MYCONSO_EMAIL}"
: "${MYCONSO_PASSWORD:?Missing environment variable MYCONSO_PASSWORD}"
: "${MYCONSO_HOUSING:?Missing environment variable MYCONSO_HOUSING}"
# Optional: set a counter ID for meter endpoints
: "${MYCONSO_COUNTER:?Missing environment variable MYCONSO_COUNTER (set to a valid counter ID for meter endpoints)}"

JSON_MODEL_DIR="json_model"
mkdir -p "$JSON_MODEL_DIR"

# Helper function to run the CLI and capture JSON output
run_cli() {
    local args=("$@")
    uv run myconsocli --email "$MYCONSO_EMAIL" --password "$MYCONSO_PASSWORD" "${args[@]}"
}

# Fetch JSON payloads for each endpoint
run_cli --auth > "$JSON_MODEL_DIR/auth.json"
run_cli --dashboard --housing-id "$MYCONSO_HOUSING" > "$JSON_MODEL_DIR/dashboard.json"
run_cli --user > "$JSON_MODEL_DIR/user.json"
run_cli --housings > "$JSON_MODEL_DIR/housings.json"
run_cli --address --housing-id "$MYCONSO_HOUSING" > "$JSON_MODEL_DIR/address.json"
run_cli --housing --housing-id "$MYCONSO_HOUSING" > "$JSON_MODEL_DIR/housing.json"
run_cli --counters > "$JSON_MODEL_DIR/counters.json"

# Example fluid type – adjust if needed
run_cli --consumption waterHot --housing-id "$MYCONSO_HOUSING" > "$JSON_MODEL_DIR/consumption_waterHot.json"
run_cli --meter-info "$MYCONSO_COUNTER" --housing-id "$MYCONSO_HOUSING" > "$JSON_MODEL_DIR/meter_info.json"
run_cli --meter "$MYCONSO_COUNTER" --housing-id "$MYCONSO_HOUSING" > "$JSON_MODEL_DIR/meter.json"

# Generate Pydantic models from the JSON json_model
generate_model() {
    local json_file=$1
    local output_file=$2
    local class_name=$3
    uv run datamodel-codegen \
        --input-file-type json \
        --output "$output_file" \
        --class-name "$class_name" \
        --field-constraints \
        --use-schema-description \
        --target-python-version 3.10 \
        --input "$json_file"
}

generate_model "$JSON_MODEL_DIR/auth.json" "myconso/models/auth.py" "Auth"
generate_model "$JSON_MODEL_DIR/dashboard.json" "myconso/models/dashboard.py" "Dashboard"
generate_model "$JSON_MODEL_DIR/user.json" "myconso/models/user.py" "User"
generate_model "$JSON_MODEL_DIR/housings.json" "myconso/models/housings.py" "Housings"
generate_model "$JSON_MODEL_DIR/address.json" "myconso/models/address.py" "Address"
generate_model "$JSON_MODEL_DIR/housing.json" "myconso/models/housing.py" "Housing"
generate_model "$JSON_MODEL_DIR/counters.json" "myconso/models/counter.py" "Counter"
generate_model "$JSON_MODEL_DIR/consumption_waterHot.json" "myconso/models/consumption.py" "Consumption"
generate_model "$JSON_MODEL_DIR/meter_info.json" "myconso/models/meter_info.py" "MeterInfo"
generate_model "$JSON_MODEL_DIR/meter.json" "myconso/models/meter.py" "Meter"

echo "Model generation complete."
