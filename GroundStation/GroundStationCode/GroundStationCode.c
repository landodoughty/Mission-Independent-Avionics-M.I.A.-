#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "hardware/spi.h"
#include "hardware/dma.h"
#include "hardware/pio.h"

// --- Third-party FatFS SD Library Components ---
#include "ff.h"
#include "hw_config.h"

// =========================================================================
// INTERFACE 1: SPI0 DMA Struct Logger (To Raspberry Pi)
// =========================================================================
#define SPI_PORT       spi0
#define PIN_MISO       16
#define PIN_CS         17
#define PIN_SCK        18
#define PIN_MOSI       19
#define BAUD_RATE      5000000 // 5 MHz

typedef struct __attribute__((packed)) {
    uint32_t timestamp;
    float temperature;
    float accelerometer_x;
    uint16_t status_flags;
} DataLogPacket;

DataLogPacket live_data;
DataLogPacket dma_buffer;
int spi_dma_chan;

void init_spi0_dma() {
    spi_init(SPI_PORT, BAUD_RATE);
    gpio_set_function(PIN_MISO, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SCK, GPIO_FUNC_SPI);
    gpio_set_function(PIN_MOSI, GPIO_FUNC_SPI);
    gpio_set_function(PIN_CS, GPIO_FUNC_SPI); // Hardware managed CS

    spi_dma_chan = dma_claim_unused_channel(true);
    dma_channel_config config = dma_channel_get_default_config(spi_dma_chan);
    channel_config_set_transfer_data_size(&config, DMA_SIZE_8);
    channel_config_set_read_increment(&config, true);
    channel_config_set_write_increment(&config, false);
    channel_config_set_dreq(&config, spi_get_dreq(SPI_PORT, true));

    dma_channel_configure(
        spi_dma_chan, &config,
        &spi_get_hw(SPI_PORT)->dr, 
        NULL, sizeof(DataLogPacket), false
    );
}

void try_trigger_spi_dma_log() {
    if (dma_channel_is_busy(spi_dma_chan)) return;
    memcpy(&dma_buffer, &live_data, sizeof(DataLogPacket));
    dma_channel_set_read_addr(spi_dma_chan, &dma_buffer, true);
}

// =========================================================================
// MAIN EXECUTION
// =========================================================================
int main() {
    stdio_init_all();
    
    // Initialize our background structural SPI connection
    init_spi0_dma();

    printf("Initializing SD card via FatFS (PIO/DMA enabled automatically if configured)...\n");

    // Initialize FatFS hardware using the bindings in your hw_config.c
    sd_card_t *pSD = sd_get_by_num(0);
    FRESULT fr = f_mount(&pSD->fatfs, pSD->pcName, 1);
    
    if (fr != FR_OK) {
        printf("Error: SD Card mount failed (%d)\n", fr);
        while (true) { tight_loop_contents(); }
    }
    printf("SD card initialized successfully.\n");

    FIL dataFile;
    int i = 0;
    bool updated = false;

    while (true) {
        // 1. Process asynchronous Struct Data (SPI0 DMA)
        live_data.timestamp = to_ms_since_boot(get_absolute_time());
        live_data.temperature = 24.5f + (i * 0.01f);
        live_data.accelerometer_x = -0.42f;
        live_data.status_flags = 0xABCD;
        
        updated = true;
        if (updated) {
            try_trigger_spi_dma_log();
            updated = false;
        }

        // 2. Process File Writing Data (PIO SD Card)
        // Format string equivalent to your previous logic
        char log_buffer[64];
        snprintf(log_buffer, sizeof(log_buffer), "testing data log %d\n", i);
        i++;

        // Open file in Append/Write-Always mode
        fr = f_open(&dataFile, "datalog.txt", FA_WRITE | FA_OPEN_APPEND);
        if (fr == FR_OK) {
            UINT bytes_written;
            // Writes out blocks utilizing background DMA transfers over PIO pins
            f_write(&dataFile, log_buffer, strlen(log_buffer), &bytes_written);
            f_close(&dataFile);
            
            printf("%s", log_buffer);
        } else {
            printf("Error opening datalog.txt (%d)\n", fr);
        }

        sleep_ms(100);
    }
}