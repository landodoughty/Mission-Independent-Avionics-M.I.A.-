#include <SPI.h>
#include <RH_RF95.h>

#define RFM95_CS   10
#define RFM95_RST  9
#define RFM95_INT  2

#define RF95_FREQ 915.0

RH_RF95 rf95(RFM95_CS, RFM95_INT);

// --- FLIGHT STATE MACHINE ---
enum FlightState : uint8_t {
  STATE_IDLE           = 0,  // Bidirectional (1Hz TX, Listening)
  STATE_ARMED          = 1,  // Bidirectional (1Hz TX, Listening)
  STATE_POWERED_ASCENT = 2,  // Unidirectional (Spam TX, Zero Listening)
  STATE_COASTING       = 3,  // Unidirectional (Spam TX, Zero Listening)
  STATE_DESCENT        = 4,  // Unidirectional (Spam TX, Zero Listening)
  STATE_RECOVERY       = 5   // Unidirectional (Spam TX, Zero Listening)
};

// Target Command Actions embedded inside updateData.target_action
enum CommandAction : uint8_t {
  ACTION_NONE   = 0,
  ACTION_ARM    = 1,
  ACTION_DISARM = 2,
  ACTION_LAUNCH = 3,
  ACTION_RESET  = 4
};

struct __attribute__((packed)) tlmData {
  float x_pos; float y_pos; float z_pos;
  float x_vel; float y_vel; float z_vel;
  float x_acc; float y_acc; float z_acc;
  float pitch; float roll;  float yaw;
  float altitude;
  float temperature;
  uint8_t current_state; // Transmits the active FlightState
}; 

struct __attribute__((packed)) updateData {
  uint32_t command_id;
  float setting_alpha;
  float setting_beta;
  uint8_t target_action; // Tells transmitter to ARM, DISARM, LAUNCH, or RESET
};

FlightState currentState = STATE_IDLE;
bool isTransmitting = false;

unsigned long lastTxTime = 0;
const unsigned long biTxInterval = 1000; 

// Landing Verification Watchdog Timers
unsigned long recoveryTimer = 0;
bool trackingRecovery = false;

// Speed calculation benchmarks
unsigned long hzTimer = 0;
unsigned long packetCount = 0;

void setup() {
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH);

  Serial.begin(115200);
  delay(100);

  digitalWrite(RFM95_RST, LOW);
  delay(10);
  digitalWrite(RFM95_RST, HIGH);
  delay(10);

  if (!rf95.init()) {
    while (1);
  }
  rf95.setFrequency(RF95_FREQ);
  rf95.setTxPower(23, false);
  
  Serial.println("Transmitter online. Initialized in IDLE state.");
}

void loop() {
  
  // Determine over-the-air cadence archetype
  bool isBidirectionalMode = (currentState == STATE_IDLE || currentState == STATE_ARMED);

  // =================================================================
  // 1. STATE TRACKING: Handle completion of physical transmission
  // =================================================================
  if (isTransmitting) {
    if (rf95.mode() != RHGenericDriver::RHModeTx) {
      isTransmitting = false; 
      
      if (isBidirectionalMode) {
        rf95.setModeRx(); 
      }
    }
  }

  // =================================================================
  // 2. RECEIVE CHECK & STRUCT TRANSITIONS (Only active in Bidir modes)
  // =================================================================
  if (isBidirectionalMode && !isTransmitting && rf95.available()) {
    uint8_t buf[sizeof(updateData)]; 
    uint8_t len = sizeof(buf);

    if (rf95.recv(buf, &len)) {
      if (len == sizeof(updateData)) {
        updateData incomingUpdate;
        memcpy(&incomingUpdate, buf, sizeof(updateData));

        // Process discrete software actions
        if (incomingUpdate.target_action == ACTION_ARM && currentState == STATE_IDLE) {
          currentState = STATE_ARMED;
          Serial.println("--> State Transition: IDLE to ARMED via command.");
        } 
        else if (incomingUpdate.target_action == ACTION_DISARM && currentState == STATE_ARMED) {
          currentState = STATE_IDLE;
          Serial.println("--> State Transition: ARMED to IDLE via command.");
        } 
        else if (incomingUpdate.target_action == ACTION_LAUNCH && currentState == STATE_ARMED) {
          currentState = STATE_POWERED_ASCENT;
          Serial.println("--> Launch Command Accepted! Transitioning to POWERED ASCENT.");
          hzTimer = millis();
          packetCount = 0;
        }
      }
    }
  }

  // =================================================================
  // 3. PHYSICAL ENVIRONMENT THRESHOLD TRANSITIONS (Unidirectional)
  // =================================================================
  // Set up mock flight path telemetry vector fields
  float z_acceleration = 15.0; // Simulated values defaults
  float z_velocity = 50.0;
  float total_velocity_magnitude = 45.0;

  if (currentState == STATE_POWERED_ASCENT) {
    // Simulated Flight profiles override
    z_acceleration = -2.5; // Emulate burnout transition trigger
    
    if (z_acceleration < 0.0) {
      currentState = STATE_COASTING;
      Serial.println("--> Flight Event: Burnout Detected (Az < 0). State = COASTING");
    }
  } 
  else if (currentState == STATE_COASTING) {
    z_velocity = -1.2; // Emulate apogee transition trigger
    
    if (z_velocity < 0.0) {
      currentState = STATE_DESCENT;
      Serial.println("--> Flight Event: Apogee Reached (Vz < 0). State = DESCENT");
    }
  } 
  else if (currentState == STATE_DESCENT) {
    total_velocity_magnitude = 0.4; // Emulate Touchdown stabilization trigger

    if (total_velocity_magnitude < 1.0) {
      if (!trackingRecovery) {
        trackingRecovery = true;
        recoveryTimer = millis(); // Start the 1 second countdown latch
      } else if (millis() - recoveryTimer >= 1000) {
        currentState = STATE_RECOVERY;
        trackingRecovery = false;
        Serial.println("--> Flight Event: Touchdown Confirmed (Mag < 1m/s for >1s). State = RECOVERY");
      }
    } else {
      trackingRecovery = false; // Reset if speed spikes back up
    }
  }

  // Allow over-the-air raw hardware breaks via emergency reset line (if added inside testing loop)
  // To handle 'reset', we can let a manual serial input force it back on the rocket:
  if (Serial.available() > 0) {
    String localCmd = Serial.readStringUntil('\n');
    localCmd.trim();
    if (localCmd.equalsIgnoreCase("reset")) {
      currentState = STATE_IDLE;
      Serial.println("--> Hard local reset applied. Reverting to IDLE.");
    }
  }

  // =================================================================
  // 4. DYNAMIC TX CADENCE
  // =================================================================
  bool shouldTransmit = false;

  if (!isTransmitting) {
    if (!isBidirectionalMode) {
      shouldTransmit = true; // Spam as fast as hardware register can cycle
    } 
    else if (millis() - lastTxTime >= biTxInterval) {
      shouldTransmit = true;
      lastTxTime = millis();
    }
  }

  if (shouldTransmit) {
    tlmData myTelemetry;
    
    // Inject constants into dataset strings
    myTelemetry.x_pos = 0.0;             myTelemetry.y_pos = 0.0;           myTelemetry.z_pos = 10.0;
    myTelemetry.x_vel = 0.0;             myTelemetry.y_vel = 0.0;           myTelemetry.z_vel = z_velocity;
    myTelemetry.x_acc = 0.0;             myTelemetry.y_acc = 0.0;           myTelemetry.z_acc = z_acceleration;
    myTelemetry.pitch = 0.0;             myTelemetry.roll  = 0.0;           myTelemetry.yaw   = 0.0;
    myTelemetry.altitude = 1500.0; 
    myTelemetry.temperature = 18.2;
    myTelemetry.current_state = (uint8_t)currentState; 

    rf95.send((uint8_t*)&myTelemetry, sizeof(myTelemetry));
    isTransmitting = true; 

    if (!isBidirectionalMode) {
      packetCount++;
    }
  }

  // =================================================================
  // 5. THROUGHPUT BENCHMARK PRINTER
  // =================================================================
  if (!isBidirectionalMode && (millis() - hzTimer >= 1000)) {
    float actualTimeElapsed = (millis() - hzTimer) / 1000.0;
    float calculatedHz = (float)packetCount / actualTimeElapsed;

    Serial.print("[SPAM HZ] State: "); Serial.print(currentState);
    Serial.print(" | Yield Output: "); Serial.print(calculatedHz, 1); Serial.println(" Hz");

    packetCount = 0;
    hzTimer = millis();
  }
}