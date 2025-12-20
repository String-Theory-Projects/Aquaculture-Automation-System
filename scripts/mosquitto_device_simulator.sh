#!/bin/bash
# MQTT Device Simulator for AquaGain Starter
# Mimics the IoT firmware device behavior using mosquitto clients
#
# Device: AquaGain Starter
# Device ID: EC:E3:34:1C:41:34
# Broker: broker.emqx.io:1883

DEVICE_ID="EC:E3:34:1C:41:34"
BROKER_HOST="broker.emqx.io"
BROKER_PORT="1883"
MQTT_PASSWORD="7-33@98:epY}"
TOPIC_PREFIX="ff"

# Topic definitions
STARTUP_TOPIC="${TOPIC_PREFIX}/${DEVICE_ID}/startup"
HEARTBEAT_TOPIC="${TOPIC_PREFIX}/${DEVICE_ID}/heartbeat"
SENSORS_TOPIC="${TOPIC_PREFIX}/${DEVICE_ID}/sensors"
COMMANDS_TOPIC="${TOPIC_PREFIX}/${DEVICE_ID}/commands"
ACK_TOPIC="${TOPIC_PREFIX}/${DEVICE_ID}/ack"
COMPLETE_TOPIC="${TOPIC_PREFIX}/${DEVICE_ID}/complete"
ALERTS_TOPIC="${TOPIC_PREFIX}/${DEVICE_ID}/alerts"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== MQTT Device Simulator: AquaGain Starter ===${NC}"
echo -e "Device ID: ${GREEN}${DEVICE_ID}${NC}"
echo -e "Broker: ${GREEN}${BROKER_HOST}:${BROKER_PORT}${NC}"
echo ""

# Function to get current timestamp in ISO format
get_timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Function to publish startup message
publish_startup() {
    local timestamp=$(get_timestamp)
    local message=$(cat <<EOF
{
  "device_id": "${DEVICE_ID}",
  "timestamp": "${timestamp}",
  "firmware_version": "1.0.0",
  "wifi_ssid": "TestWiFi",
  "wifi_signal_strength": -45
}
EOF
)
    echo -e "${YELLOW}Publishing startup message...${NC}"
    mosquitto_pub -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
        -u "${DEVICE_ID}" -P "${MQTT_PASSWORD}" \
        -t "${STARTUP_TOPIC}" -m "${message}" -q 2
    echo -e "${GREEN}✓ Startup message published${NC}\n"
}

# Function to publish heartbeat
publish_heartbeat() {
    local timestamp=$(get_timestamp)
    local message=$(cat <<EOF
{
  "device_id": "${DEVICE_ID}",
  "timestamp": "${timestamp}",
  "firmware_version": "1.0.0",
  "wifi_ssid": "TestWiFi",
  "wifi_signal_strength": -45,
  "free_heap": 250000
}
EOF
)
    echo -e "${YELLOW}Publishing heartbeat...${NC}"
    mosquitto_pub -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
        -u "${DEVICE_ID}" -P "${MQTT_PASSWORD}" \
        -t "${HEARTBEAT_TOPIC}" -m "${message}" -q 2
    echo -e "${GREEN}✓ Heartbeat published${NC}\n"
}

# Function to publish sensor data (Message 1: Temperature, DO, pH, Battery)
publish_sensor_data_1() {
    local timestamp=$(get_timestamp)
    local temp=$((20 + RANDOM % 10))  # 20-30°C
    local do_val=$(awk "BEGIN {printf \"%.2f\", 5 + rand() * 5}")  # 5-10 mg/L
    local ph=$(awk "BEGIN {printf \"%.2f\", 6.5 + rand() * 1.5}")  # 6.5-8.0
    local battery=$((80 + RANDOM % 20))  # 80-100%
    
    local message=$(cat <<EOF
{
  "device_id": "${DEVICE_ID}",
  "timestamp": "${timestamp}",
  "data": {
    "temperature": ${temp},
    "dissolved_oxygen": ${do_val},
    "ph": ${ph},
    "battery": ${battery}
  },
  "metadata": {
    "firmware_version": "1.0.0",
    "hardware_version": "ESP32-WROOM-32"
  }
}
EOF
)
    echo -e "${YELLOW}Publishing sensor data (Message 1: Temp, DO, pH, Battery)...${NC}"
    mosquitto_pub -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
        -u "${DEVICE_ID}" -P "${MQTT_PASSWORD}" \
        -t "${SENSORS_TOPIC}" -m "${message}" -q 2
    echo -e "${GREEN}✓ Sensor data message 1 published${NC}\n"
}

# Function to publish sensor data (Message 2: Water levels and Feed levels)
publish_sensor_data_2() {
    local timestamp=$(get_timestamp)
    local water1=$(awk "BEGIN {printf \"%.2f\", 50 + rand() * 30}")  # 50-80 cm
    local water2=$(awk "BEGIN {printf \"%.2f\", 50 + rand() * 30}")  # 50-80 cm
    local feed1=$((60 + RANDOM % 30))  # 60-90%
    local feed2=$((60 + RANDOM % 30))  # 60-90%
    
    local message=$(cat <<EOF
{
  "device_id": "${DEVICE_ID}",
  "timestamp": "${timestamp}",
  "data": {
    "water1": ${water1},
    "water2": ${water2},
    "feed1": ${feed1},
    "feed2": ${feed2}
  },
  "metadata": {
    "firmware_version": "1.0.0",
    "signal": -45
  }
}
EOF
)
    echo -e "${YELLOW}Publishing sensor data (Message 2: Water/Feed levels)...${NC}"
    mosquitto_pub -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
        -u "${DEVICE_ID}" -P "${MQTT_PASSWORD}" \
        -t "${SENSORS_TOPIC}" -m "${message}" -q 2
    echo -e "${GREEN}✓ Sensor data message 2 published${NC}\n"
}

# Function to publish command acknowledgment
publish_command_ack() {
    local command_id=$1
    local success=${2:-true}
    local timestamp=$(get_timestamp)
    
    local message=$(cat <<EOF
{
  "device_id": "${DEVICE_ID}",
  "command_id": "${command_id}",
  "success": "${success}",
  "timestamp": "${timestamp}",
  "message": "Command executed successfully"
}
EOF
)
    echo -e "${YELLOW}Publishing command ACK for ${command_id}...${NC}"
    mosquitto_pub -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
        -u "${DEVICE_ID}" -P "${MQTT_PASSWORD}" \
        -t "${ACK_TOPIC}" -m "${message}" -q 2
    echo -e "${GREEN}✓ Command ACK published${NC}\n"
}

# Function to publish command completion
publish_command_complete() {
    local command_id=$1
    local success=${2:-true}
    local execution_time=${3:-5000}
    local timestamp=$(get_timestamp)
    
    local message=$(cat <<EOF
{
  "device_id": "${DEVICE_ID}",
  "command_id": "${command_id}",
  "success": "${success}",
  "timestamp": "${timestamp}",
  "execution_time_ms": ${execution_time}
}
EOF
)
    echo -e "${YELLOW}Publishing command completion for ${command_id}...${NC}"
    mosquitto_pub -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
        -u "${DEVICE_ID}" -P "${MQTT_PASSWORD}" \
        -t "${COMPLETE_TOPIC}" -m "${message}" -q 2
    echo -e "${GREEN}✓ Command completion published${NC}\n"
}

# Function to subscribe to commands (runs in background)
subscribe_to_commands() {
    echo -e "${YELLOW}Subscribing to commands topic: ${COMMANDS_TOPIC}${NC}"
    echo -e "${BLUE}Listening for commands (press Ctrl+C to stop)...${NC}"
    echo -e "${GREEN}Auto-responding with ACK and completion messages${NC}\n"
    
    mosquitto_sub -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
        -u "${DEVICE_ID}" -P "${MQTT_PASSWORD}" \
        -t "${COMMANDS_TOPIC}" -q 2 \
        -v | while read -r line; do
            # Extract topic and message (mosquitto_sub -v prints "topic message")
            topic=$(echo "$line" | cut -d' ' -f1)
            message=$(echo "$line" | cut -d' ' -f2-)
            
            echo -e "${GREEN}📥 Received command on ${topic}:${NC}"
            echo -e "${BLUE}${message}${NC}\n"
            
            # Extract command_id from JSON using multiple methods for reliability
            command_id=$(echo "$message" | grep -o '"command_id"[[:space:]]*:[[:space:]]*"[^"]*"' | grep -o '"[^"]*"' | tail -1 | tr -d '"')
            
            # Fallback: try without quotes
            if [ -z "$command_id" ]; then
                command_id=$(echo "$message" | grep -o '"command_id"[[:space:]]*:[[:space:]]*[^,}]*' | grep -o '[^:]*$' | tr -d ' "')
            fi
            
            if [ -n "$command_id" ]; then
                echo -e "${YELLOW}🔄 Processing command: ${command_id}${NC}"
                
                # Immediately send acknowledgment (always successful)
                echo -e "${YELLOW}  → Sending ACK...${NC}"
                publish_command_ack "$command_id" "true"
                
                # Simulate command execution delay (1-3 seconds)
                execution_time=$((1000 + RANDOM % 2000))
                sleep_duration=$(awk "BEGIN {printf \"%.2f\", $execution_time / 1000}")
                echo -e "${YELLOW}  → Simulating execution (${sleep_duration}s)...${NC}"
                sleep "$sleep_duration"
                
                # Send completion message (always successful)
                echo -e "${YELLOW}  → Sending completion...${NC}"
                publish_command_complete "$command_id" "true" "$execution_time"
                
                echo -e "${GREEN}✓ Command ${command_id} processed successfully${NC}\n"
            else
                echo -e "${YELLOW}⚠️  Could not extract command_id from message${NC}"
                echo -e "${BLUE}Message: ${message}${NC}\n"
            fi
        done
}

# Main menu
show_menu() {
    echo -e "\n${BLUE}=== Available Commands ===${NC}"
    echo "1) Publish startup message"
    echo "2) Publish heartbeat"
    echo "3) Publish sensor data (Message 1: Temp, DO, pH, Battery)"
    echo "4) Publish sensor data (Message 2: Water/Feed levels)"
    echo "5) Publish both sensor data messages"
    echo "6) Subscribe to commands (interactive)"
    echo "7) Run continuous simulation (startup + periodic heartbeat + sensor data)"
    echo "8) Exit"
    echo ""
    read -p "Select option [1-8]: " choice
}

# Continuous simulation mode
run_continuous_simulation() {
    echo -e "${BLUE}Starting continuous simulation...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo -e "${GREEN}Auto-responding to all commands with ACK and completion${NC}\n"
    
    # Publish startup
    publish_startup
    sleep 2
    
    # Start command subscriber in background (with auto-response)
    (
        mosquitto_sub -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
            -u "${DEVICE_ID}" -P "${MQTT_PASSWORD}" \
            -t "${COMMANDS_TOPIC}" -q 2 \
            -v | while read -r line; do
                # Extract topic and message
                topic=$(echo "$line" | cut -d' ' -f1)
                message=$(echo "$line" | cut -d' ' -f2-)
                
                echo -e "${GREEN}📥 Received command:${NC} ${message}"
                
                # Extract command_id from JSON
                command_id=$(echo "$message" | grep -o '"command_id"[[:space:]]*:[[:space:]]*"[^"]*"' | grep -o '"[^"]*"' | tail -1 | tr -d '"')
                
                if [ -z "$command_id" ]; then
                    command_id=$(echo "$message" | grep -o '"command_id"[[:space:]]*:[[:space:]]*[^,}]*' | grep -o '[^:]*$' | tr -d ' "')
                fi
                
                if [ -n "$command_id" ]; then
                    # Immediately send acknowledgment (always successful)
                    local timestamp=$(get_timestamp)
                    local ack_msg=$(cat <<EOF
{
  "device_id": "${DEVICE_ID}",
  "command_id": "${command_id}",
  "success": "true",
  "timestamp": "${timestamp}",
  "message": "Command executed successfully"
}
EOF
)
                    mosquitto_pub -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
                        -u "${DEVICE_ID}" -P "${MQTT_PASSWORD}" \
                        -t "${ACK_TOPIC}" -m "${ack_msg}" -q 2 >/dev/null 2>&1
                    
                    echo -e "${YELLOW}  ✓ ACK sent for ${command_id}${NC}"
                    
                    # Simulate execution delay (1-3 seconds)
                    local execution_time=$((30000 + RANDOM % 2000))
                    sleep $(awk "BEGIN {printf \"%.2f\", $execution_time / 1000}")
                    
                    # Send completion message (always successful)
                    timestamp=$(get_timestamp)
                    local complete_msg=$(cat <<EOF
{
  "device_id": "${DEVICE_ID}",
  "command_id": "${command_id}",
  "success": "true",
  "timestamp": "${timestamp}",
  "execution_time_ms": ${execution_time}
}
EOF
)
                    mosquitto_pub -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
                        -u "${DEVICE_ID}" -P "${MQTT_PASSWORD}" \
                        -t "${COMPLETE_TOPIC}" -m "${complete_msg}" -q 2 >/dev/null 2>&1
                    
                    echo -e "${GREEN}  ✓ Completion sent for ${command_id} (${execution_time}ms)${NC}\n"
                fi
            done
    ) &
    SUBSCRIBER_PID=$!
    
    # Main loop: publish heartbeat every 20s, sensor data every 30s
    local heartbeat_counter=0
    local sensor_counter=0
    
    # Trap to cleanup on exit
    trap "kill $SUBSCRIBER_PID 2>/dev/null; exit" INT TERM
    
    while true; do
        sleep 1
        heartbeat_counter=$((heartbeat_counter + 1))
        sensor_counter=$((sensor_counter + 1))
        
        # Publish heartbeat every 20 seconds
        if [ $heartbeat_counter -ge 20 ]; then
            publish_heartbeat
            heartbeat_counter=0
        fi
        
        # Publish sensor data every 30 seconds
        if [ $sensor_counter -ge 30 ]; then
            publish_sensor_data_1
            sleep 1
            publish_sensor_data_2
            sensor_counter=0
        fi
    done
}

# Main execution
if [ $# -eq 0 ]; then
    # Interactive mode
    while true; do
        show_menu
        case $choice in
            1) publish_startup ;;
            2) publish_heartbeat ;;
            3) publish_sensor_data_1 ;;
            4) publish_sensor_data_2 ;;
            5) 
                publish_sensor_data_1
                sleep 1
                publish_sensor_data_2
                ;;
            6) subscribe_to_commands ;;
            7) run_continuous_simulation ;;
            8) 
                echo -e "${GREEN}Exiting...${NC}"
                exit 0
                ;;
            *) 
                echo -e "${YELLOW}Invalid option. Please try again.${NC}"
                ;;
        esac
    done
else
    # Command-line mode
    case "$1" in
        startup) publish_startup ;;
        heartbeat) publish_heartbeat ;;
        sensors1) publish_sensor_data_1 ;;
        sensors2) publish_sensor_data_2 ;;
        sensors) 
            publish_sensor_data_1
            sleep 1
            publish_sensor_data_2
            ;;
        subscribe) subscribe_to_commands ;;
        simulate) run_continuous_simulation ;;
        ack)
            if [ -z "$2" ]; then
                echo "Usage: $0 ack <command_id> [success]"
                exit 1
            fi
            publish_command_ack "$2" "${3:-true}"
            ;;
        complete)
            if [ -z "$2" ]; then
                echo "Usage: $0 complete <command_id> [success] [execution_time_ms]"
                exit 1
            fi
            publish_command_complete "$2" "${3:-true}" "${4:-5000}"
            ;;
        *)
            echo "Usage: $0 [startup|heartbeat|sensors|sensors1|sensors2|subscribe|simulate|ack|complete]"
            echo ""
            echo "Examples:"
            echo "  $0 startup              # Publish startup message"
            echo "  $0 heartbeat            # Publish heartbeat"
            echo "  $0 sensors             # Publish both sensor data messages"
            echo "  $0 subscribe            # Subscribe to commands"
            echo "  $0 simulate            # Run continuous simulation"
            echo "  $0 ack <command_id>    # Publish command ACK"
            echo "  $0 complete <command_id> # Publish command completion"
            exit 1
            ;;
    esac
fi
