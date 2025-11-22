//! This example test the RP Pico W on board LED.
//!
//! It does not work with the RP Pico board. See blinky.rs.

#![no_std]
#![no_main]

use cyw43_pio::{DEFAULT_CLOCK_DIVIDER, PioSpi};
use defmt::*;
use embassy_executor::Spawner;
use embassy_rp::bind_interrupts;
use embassy_rp::gpio::{Level, Output, Input, Pull};
use embassy_rp::peripherals::{DMA_CH0, PIO0};
use embassy_rp::pio::{InterruptHandler, Pio};
use mipidsi::models::ST7735s;
use static_cell::StaticCell;
use {defmt_rtt as _, panic_probe as _};
use embassy_rp::spi::{Spi, Config as SpiConfig};
use embassy_sync::blocking_mutex::raw::NoopRawMutex;
use display_interface_spi::SPIInterface;
use mipidsi::Builder;
use embedded_graphics::{
    mono_font::{
        ascii::{FONT_10X20, FONT_5X8, FONT_6X12, FONT_9X15},
        MonoTextStyle, MonoTextStyleBuilder,
    },
    pixelcolor::BinaryColor,
    pixelcolor::Rgb565,
    prelude::*,
    text::Text,
};
use core::cell::RefCell;
use embassy_embedded_hal::shared_bus::blocking::spi::SpiDeviceWithConfig;

use embassy_sync::blocking_mutex::Mutex;


bind_interrupts!(struct Irqs {
    PIO0_IRQ_0 => InterruptHandler<PIO0>;
});

#[embassy_executor::task]
async fn cyw43_task(runner: cyw43::Runner<'static, Output<'static>, PioSpi<'static, PIO0, 0, DMA_CH0>>) -> ! {
    runner.run().await
}



async fn text(text: &str, x: i32, y: i32) -> Text<'_, MonoTextStyle<'_, BinaryColor>> {
    let style = MonoTextStyleBuilder::new()
        .font(&FONT_5X8)
        .text_color(BinaryColor::Off)
        .build();
    Text::new(
        text,
        Point::new(x, y),
        style        
    )
}

#[embassy_executor::main]
async fn main(spawner: Spawner) {
    let p = embassy_rp::init(Default::default());
    let fw = include_bytes!("../wifi_firmware/43439A0.bin");
    let clm = include_bytes!("../wifi_firmware/43439A0_clm.bin");

    // To make flashing faster for development, you may want to flash the firmwares independently
    // at hardcoded addresses, instead of baking them into the program with `include_bytes!`:
    //     probe-rs download ../../cyw43-firmware/43439A0.bin --binary-format bin --chip RP2040 --base-address 0x10100000
    //     probe-rs download ../../cyw43-firmware/43439A0_clm.bin --binary-format bin --chip RP2040 --base-address 0x10140000
    //let fw = unsafe { core::slice::from_raw_parts(0x10100000 as *const u8, 230321) };
    //let clm = unsafe { core::slice::from_raw_parts(0x10140000 as *const u8, 4752) };

    let pwr = Output::new(p.PIN_23, Level::Low);
    let cs = Output::new(p.PIN_25, Level::High);
    let mut pio = Pio::new(p.PIO0, Irqs);
    let spi = PioSpi::new(
        &mut pio.common,
        pio.sm0,
        DEFAULT_CLOCK_DIVIDER,
        pio.irq0,
        cs,
        p.PIN_24,
        p.PIN_29,
        p.DMA_CH0,
    );
    let w = Input::new(p.PIN_5, Pull::Up);
    let a = Input::new(p.PIN_6, Pull::Up);
    let s = Input::new(p.PIN_7, Pull::Up);
    let d = Input::new(p.PIN_8, Pull::Up);
    let i = Input::new(p.PIN_12, Pull::Up);
    let j = Input::new(p.PIN_13, Pull::Up);
    let k = Input::new(p.PIN_14, Pull::Up);
    let l = Input::new(p.PIN_15, Pull::Up);

    static STATE: StaticCell<cyw43::State> = StaticCell::new();
    let state = STATE.init(cyw43::State::new());
    let (_net_device, mut control, runner) = cyw43::new(state, pwr, spi, fw).await;
    spawner.spawn(cyw43_task(runner)).unwrap();


    let mut display_config = SpiConfig::default();
    display_config.frequency = 16_000_000; // 16 MHz
    
    let spi = Spi::new_blocking(
        p.SPI0,
        p.PIN_18, // SCK
        p.PIN_19, // MOSI
        p.PIN_16, // MISO
        display_config.clone(),
    );
    let spi_bus: Mutex<NoopRawMutex, _> = Mutex::new(RefCell::new(spi));

    let dc = Output::new(p.PIN_22, Level::Low);
    let rst = Output::new(p.PIN_26, Level::Low);
    let cs = Output::new(p.PIN_20, Level::High);

    let display_spi = SpiDeviceWithConfig::new(&spi_bus, cs, display_config);

    // create display interface with buffer
    let buffer = [0u8; 512];
    let di = SPIInterface::new(display_spi, dc);

    let mut display = Builder::new(ST7735s, di)
        .reset_pin(rst)
        .init(&mut embassy_time::Delay)
        .unwrap();
    
    // test it out
    display.clear(Rgb565::RED).unwrap();

    control.init(clm).await;
    control
        .set_power_management(cyw43::PowerManagementMode::PowerSave)
        .await;

    loop {
        if w.is_high() {
            info!("led on!");
            control.gpio_set(0, true).await;  
            display.clear(Rgb565::RED).unwrap(); 
        }
        else {
            info!("led off!");
            control.gpio_set(0, false).await;
            display.clear(Rgb565::BLACK).unwrap();
            text("led on!", 10, 10).await;
        }

    }
}