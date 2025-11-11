//! This example test the RP Pico W on board LED.
//!
//! It does not work with the RP Pico board. See blinky.rs.

#![no_std]
#![no_main]

use embedded_graphics::{
    pixelcolor::Rgb565,
    prelude::*,
    primitives::{Circle, PrimitiveStyle},
    mono_font::{ascii::FONT_6X10, MonoTextStyle},
    text::{Alignment, Text},
};
use cyw43_pio::{DEFAULT_CLOCK_DIVIDER, PioSpi};
use defmt::*;
use embassy_executor::Spawner;
use embassy_rp::bind_interrupts;
use embassy_rp::spi::Spi;
use embassy_rp::spi;
use embassy_rp::gpio::{Level, Output};
use embassy_rp::peripherals::{DMA_CH0, PIO0};
use embassy_rp::pio::{InterruptHandler, Pio};
use embassy_time::{Duration, Timer};
use st7735_lcd_doublebuffering::ST7735Buffered;
use static_cell::StaticCell;
use {defmt_rtt as _, panic_probe as _};

bind_interrupts!(struct Irqs {
    PIO0_IRQ_0 => InterruptHandler<PIO0>;
});

#[embassy_executor::task]
async fn cyw43_task(runner: cyw43::Runner<'static, Output<'static>, PioSpi<'static, PIO0, 0, DMA_CH0>>) -> ! {
    runner.run().await
}

#[embassy_executor::main]
async fn main(spawner: Spawner) {
    let p = embassy_rp::init(Default::default());
    let fw = include_bytes!("../wifi_firmware/43439A0.bin");
    let clm = include_bytes!("../wifi_firmware/43439A0_clm.bin");
    let rgb = true;
    let width = 160;
    let height = 128;
    
    // To make flashing faster for development, you may want to flash the firmwares independently
    // at hardcoded addresses, instead of baking them into the program with `include_bytes!`:
    //     probe-rs download ../../cyw43-firmware/43439A0.bin --binary-format bin --chip RP2040 --base-address 0x10100000
    //     probe-rs download ../../cyw43-firmware/43439A0_clm.bin --binary-format bin --chip RP2040 --base-address 0x10140000
    //let fw = unsafe { core::slice::from_raw_parts(0x10100000 as *const u8, 230321) };
    //let clm = unsafe { core::slice::from_raw_parts(0x10140000 as *const u8, 4752) };
    let spi_sclk = p.PIN_18;
    let spi_mosi = p.PIN_19;
    let spi_miso = p.PIN_16;
    let spi_cs = p.PIN_20;
    let pwr = Output::new(p.PIN_23, Level::Low);
    let cs = Output::new(p.PIN_25, Level::High);
    let mut pio = Pio::new(p.PIO0, Irqs);


    let dc = p.PIN_22;
    let rst = p.PIN_26;

    // Exchange the uninitialised SPI driver for an initialised one
    let mut config = spi::Config::default();
    config.frequency = 64_000_000;
    let mut spi = Spi::new_blocking(p.SPI0, spi_sclk, spi_mosi, spi_miso, config);

    let mut display = ST7735Buffered::new(spi, dc, rgb, width, height);
    static STATE: StaticCell<cyw43::State> = StaticCell::new();
    let state = STATE.init(cyw43::State::new());
    let (_net_device, mut control, runner) = cyw43::new(state, pwr, spi, fw).await;
    spawner.spawn(unwrap!(cyw43_task(runner)));

    control.init(clm).await;
    control
        .set_power_management(cyw43::PowerManagementMode::PowerSave)
        .await;

    let delay = Duration::from_secs(1);
    loop {
        info!("led on!");
        control.gpio_set(0, true).await;
        Timer::after(delay).await;

        info!("led off!");
        control.gpio_set(0, false).await;
        Timer::after(delay).await;
        display.clear(Rgb565::BLACK).unwrap();
            let text = "embedded-graphics";
            Text::with_alignment(
                text,
                display.bounding_box().center() + Point::new(0, 15),
        character_style,
        Alignment::Center,
    );
        display.swap_buffers().unwrap();
    }
}
