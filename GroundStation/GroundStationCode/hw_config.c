#include "hw_config.h"

static spi_config_t spi_bus = {
    .hw_inst = spi0, // Placeholder, overridden by PIO settings below
    .miso_gpio = 4,
    .mosi_gpio = 7,
    .sck_gpio = 6,
    .baud_rate = 10 * 1000 * 1000, // 10 MHz
    
    // Enabling these two directives moves the runtime execution off 
    // the hardware SPI core block and loads it onto a PIO state machine automatically.
    .use_pio = true,
    .pio_interrupt = 0
};

static sd_card_t sd_cards[] = {
    {
        .pcName = "0:",
        .spi_if.spi = &spi_bus,
        .spi_if.ss_gpio = 5, // CS Pin
        .card_detect_gpio = -1, // Set pin number if using CD pin
        .mounted = false
    }
};

size_t sd_get_num() { return count_of(sd_cards); }
sd_card_t *sd_get_by_num(size_t num) {
    if (num <= count_of(sd_cards)) return &sd_cards[num];
    return NULL;
}