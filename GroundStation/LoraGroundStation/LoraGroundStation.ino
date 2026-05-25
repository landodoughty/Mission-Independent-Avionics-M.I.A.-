#include <SPI.h>
#include <RH_RF95.h>
#include <RHSoftwareSPI.h> 

#define RFM95_CS   13
#define RFM95_RST  21
#define RFM95_INT  20

#define SOFT_MISO  12
#define SOFT_MOSI  15
#define SOFT_SCK   14

#define RF95_FREQ 915.0

const int ledPins[] = {8, 9, 10, 11, 3};
const int numLeds = 5;

enum RadioMode : uint8_t {
  MODE_BIDIRECTIONAL  = 0,
  MODE_UNIDIRECTIONAL = 1
};

enum FlightState : uint8_t {
  STATE_IDLE           = 0,
  STATE_ARMED          = 1,
  STATE_POWERED_ASCENT = 2,
  STATE_COASTING       = 3,
  STATE_DESCENT        = 4,
  STATE_RECOVERY       = 5
};

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
  uint8_t current_state; 
}; 

struct __attribute__((packed)) updateData {
  uint32_t command_id;
  float setting_alpha;
  float setting_beta;
  uint8_t target_action; 
};

RHSoftwareSPI soft_spi;
RH_RF95 rf95(RFM95_CS, RFM95_INT, soft_spi);

RadioMode activeMode = MODE_BIDIRECTIONAL; 
bool isTransmitting = false;

unsigned long lastUpdateTxTime = 0;
const unsigned long updateTxInterval = 500; 

int finalPacketsToSend = -1; 
CommandAction latchedAction = ACTION_NONE;

unsigned long lastTlmReceivedTime = 0;
const unsigned long tlmTimeoutDuration = 3000; 
bool isConnected = false;                     

uint32_t commandCounter = 100;

void setup() {
  for (int i = 0; i < numLeds; i++) {
    pinMode(ledPins[i], OUTPUT);
    digitalWrite(ledPins[i], LOW); 
  }

  soft_spi.setPins(SOFT_MISO, SOFT_MOSI, SOFT_SCK);
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
  
  Serial.println("--- GCS Ground Receiver Initialized ---");
  Serial.println("Commands: 'arm' | 'disarm' | 'launch' | 'reset'");
  Serial.println("x_pos,y_pos,z_pos,x_vel,y_vel,z_vel,x_acc,y_acc,z_acc,pitch,roll,yaw,altitude,temperature,rocket_state,gcs_mode,rssi,snr");
  
  lastTlmReceivedTime = millis(); 
}

void loop() {
  
  // =================================================================
  // 1. STATE TRACKING: Complete over-the-air command packets
  // =================================================================
  if (isTransmitting) {
    if (rf95.mode() != RHGenericDriver::RHModeTx) {
      isTransmitting = false; 
      rf95.setModeRx(); 
      
      if (finalPacketsToSend > 0) {
        finalPacketsToSend--;
        if (finalPacketsToSend == 0) {
          if (latchedAction == ACTION_RESET) {
            activeMode = MODE_BIDIRECTIONAL;
          }
          latchedAction = ACTION_NONE; 
          finalPacketsToSend = -1; 
        }
      }
    }
  }

  // =================================================================
  // 2. RECEIVE TELEMETRY STREAM & AUTOMATED RX MODE SWITCHING
  // =================================================================
  if (!isTransmitting && rf95.available()) {
    uint8_t buf[sizeof(tlmData)]; 
    uint8_t len = sizeof(buf);

    if (rf95.recv(buf, &len)) {
      if (len == sizeof(tlmData)) {
        tlmData incomingTlm;
        memcpy(&incomingTlm, buf, sizeof(tlmData));

        lastTlmReceivedTime = millis();
        isConnected = true; 

        if (activeMode == MODE_BIDIRECTIONAL && incomingTlm.current_state >= STATE_POWERED_ASCENT) {
          activeMode = MODE_UNIDIRECTIONAL;
        }

        Serial.print(incomingTlm.x_pos, 2);          Serial.print(",");
        Serial.print(incomingTlm.y_pos, 2);          Serial.print(",");
        Serial.print(incomingTlm.z_pos, 2);          Serial.print(",");
        Serial.print(incomingTlm.x_vel, 2);          Serial.print(",");
        Serial.print(incomingTlm.y_vel, 2);          Serial.print(",");
        Serial.print(incomingTlm.z_vel, 2);          Serial.print(",");
        Serial.print(incomingTlm.x_acc, 2);          Serial.print(",");
        Serial.print(incomingTlm.y_acc, 2);          Serial.print(",");
        Serial.print(incomingTlm.z_acc, 2);          Serial.print(",");
        Serial.print(incomingTlm.pitch, 2);          Serial.print(",");
        Serial.print(incomingTlm.roll, 2);           Serial.print(",");
        Serial.print(incomingTlm.yaw, 2);            Serial.print(",");
        Serial.print(incomingTlm.altitude, 2);        Serial.print(",");
        Serial.print(incomingTlm.temperature, 2);     Serial.print(",");
        
        Serial.print(incomingTlm.current_state);      Serial.print(",");
        Serial.print((uint8_t)activeMode);            Serial.print(",");
        
        Serial.print(rf95.lastRssi());                Serial.print(",");
        Serial.println(rf95.lastSNR()); 

        int16_t RSSI = rf95.lastRssi();
        for (int i = 0; i < numLeds; i++) {
          digitalWrite(ledPins[i], (-110 + (15 * i) > RSSI) ? LOW : HIGH);
        }
      }
    }
  }

  // =================================================================
  // 3. 3-SECOND WATCHDOG CHECK
  // =================================================================
  if (isConnected && (millis() - lastTlmReceivedTime >= tlmTimeoutDuration)) {
    isConnected = false; 
    for (int i = 0; i < numLeds; i++) {
      digitalWrite(ledPins[i], LOW);
    }
  }

  // =================================================================
  // 4. OUTGOING UPDATE STRUCT STREAM 
  // =================================================================
  if (!isTransmitting) {
    bool triggerBurst = (finalPacketsToSend > 0); 
    bool triggerTimed = (activeMode == MODE_BIDIRECTIONAL && (millis() - lastUpdateTxTime >= updateTxInterval));

    if (triggerBurst || triggerTimed) {
      if (triggerTimed) lastUpdateTxTime = millis();

      updateData cmd;
      cmd.command_id = commandCounter++;
      cmd.setting_alpha = 0.0;
      cmd.setting_beta = 0.0;
      
      if (triggerBurst) {
        cmd.target_action = (uint8_t)latchedAction;
      } else {
        cmd.target_action = (uint8_t)ACTION_NONE; 
      }

      rf95.send((uint8_t*)&cmd, sizeof(cmd));
      isTransmitting = true; 
    }
  }

  // =================================================================
  // 5. FIXED: ISOLATED SERIAL MONITOR MONITOR PIPELINE
  // =================================================================
  if (Serial.available() > 0 && finalPacketsToSend == -1) {
    char inputBuf[32];
    // Read up to a newline character or buffer size limit safely
    size_t numBytes = Serial.readBytesUntil('\n', inputBuf, sizeof(inputBuf) - 1);
    
    if (numBytes > 0) {
      inputBuf[numBytes] = '\0'; // Guarantee explicit null-termination
      String commandStr = String(inputBuf);
      commandStr.trim(); // Strip carriage returns or extra spaces
      
      if (commandStr.equalsIgnoreCase("arm")) {
        latchedAction = ACTION_ARM;
        finalPacketsToSend = 2; 
      } 
      else if (commandStr.equalsIgnoreCase("disarm")) {
        latchedAction = ACTION_DISARM;
        finalPacketsToSend = 2; 
      } 
      else if (commandStr.equalsIgnoreCase("launch")) {
        if (activeMode == MODE_BIDIRECTIONAL) {
          latchedAction = ACTION_LAUNCH;
          finalPacketsToSend = 2; 
        }
      } 
      else if (commandStr.equalsIgnoreCase("reset")) {
        latchedAction = ACTION_RESET;
        finalPacketsToSend = 2; 
      }
    }
  }
}

void setup1() {}
void loop1() {}