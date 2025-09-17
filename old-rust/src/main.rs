//! # Pico Blinky Example
//!
//! Blinks the LED on a Pico board.
//!
//! This will blink an LED attached to GP25, which is the pin the Pico uses for
//! the on-board LED.
//!
//! See the `Cargo.toml` file for Copyright and license details.

#![no_std]
#![no_main]

use mipidsi::{models::ST7735s, Builder, Display, Orientation};

use display_interface_spi::SPIInterfaceNoCS;
// The macro for our start-up function
use rp_pico::{
    entry,
    hal::gpio::{FunctionSio, Pin, PullUp, SioInput, bank0::*},
};

// GPIO traits
use embedded_hal::digital::{InputPin, OutputPin};
// Ensure we halt the program on panic (if we don't mention this crate it won't
// be linked)
use panic_halt as _;

// Pull in any important traits
use rp_pico::hal::prelude::*;

// Some traits we need
//use cortex_m::prelude::*;
use embedded_canvas::CCanvasAt;
use embedded_graphics::{
    mock_display::MockDisplay,
    mono_font::{MonoTextStyle, ascii::FONT_6X10},
    pixelcolor::BinaryColor,
    pixelcolor::Rgb565,
    prelude::*,
    primitives::{
        Circle, PrimitiveStyle, PrimitiveStyleBuilder, Rectangle, StrokeAlignment, Triangle,
    },
    text::{Alignment, Text},
};
use embedded_time::fixed_point::FixedPoint;
use embedded_time::rate::Extensions;
use rp_pico::hal::clocks::Clock;
use rp_pico::hal::fugit::RateExtU32;

// A shorter alias for the Peripheral Access Crate, which provides low-level
// register access
use rp_pico::hal::pac;

use rp_pico::hal::spi;
// Import the GPIO abstraction:
use rp_pico::hal::gpio;

// A shorter alias for the Hardware Abstraction Layer, which provides
// higher-level drivers.
use rp_pico::hal;

// Input for each of the 8 buttons
struct Input {
    w: Pin<Gpio5, FunctionSio<SioInput>, PullUp>,
    a: Pin<Gpio6, FunctionSio<SioInput>, PullUp>,
    s: Pin<Gpio7, FunctionSio<SioInput>, PullUp>,
    d: Pin<Gpio8, FunctionSio<SioInput>, PullUp>,
    i: Pin<Gpio12, FunctionSio<SioInput>, PullUp>,
    j: Pin<Gpio13, FunctionSio<SioInput>, PullUp>,
    k: Pin<Gpio14, FunctionSio<SioInput>, PullUp>,
    l: Pin<Gpio15, FunctionSio<SioInput>, PullUp>,
}

/// Entry point to our bare-metal application.
///
/// The `#[entry]` macro ensures the Cortex-M start-up code calls this function
/// as soon as all global variables are initialised.
///
/// The function configures the RP2040 peripherals, then blinks the LED in an
/// infinite loop.
#[entry]
fn main() -> ! {
    // Grab our singleton objects
    let mut pac = pac::Peripherals::take().unwrap();
    let core = pac::CorePeripherals::take().unwrap();

    // Set up the watchdog driver - needed by the clock setup code
    let mut watchdog = hal::Watchdog::new(pac.WATCHDOG);

    // Step 1. Turn on the crystal.
    let xosc = hal::xosc::setup_xosc_blocking(pac.XOSC, RateExtU32::Hz(rp_pico::XOSC_CRYSTAL_FREQ))
        .map_err(|_x| false)
        .unwrap();
    // Step 2. Configure watchdog tick generation to tick over every microsecond.
    watchdog.enable_tick_generation((rp_pico::XOSC_CRYSTAL_FREQ / 1_000_000) as u8);
    // Step 3. Create a clocks manager.
    let mut clocks = hal::clocks::ClocksManager::new(pac.CLOCKS);
    // Step 4. Set up the system PLL.
    //
    // We take the Crystal Oscillator (=12 MHz) with no divider, and ×126 to
    // give a FOUTVCO of 1512 MHz. This must be in the range 750 MHz - 1600 MHz.
    // The factor of 126 is calculated automatically given the desired FOUTVCO.
    //
    // Next we ÷5 on the first post divider to give 302.4 MHz.
    //
    // Finally we ÷2 on the second post divider to give 151.2 MHz.
    //
    // We note from the [RP2040
    // Datasheet](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf),
    // Section 2.18.2.1:
    //
    // > Jitter is minimised by running the VCO at the highest possible
    // > frequency, so that higher post-divide values can be used.
    let pll_sys = hal::pll::setup_pll_blocking(
        pac.PLL_SYS,
        xosc.operating_frequency(),
        hal::pll::PLLConfig {
            vco_freq: RateExtU32::MHz(1380),
            refdiv: 1,
            post_div1: 3,
            post_div2: 2,
        },
        &mut clocks,
        &mut pac.RESETS,
    )
    .map_err(|_x| false)
    .unwrap();
    // Step 5. Set up a 48 MHz PLL for the USB system.
    let pll_usb = hal::pll::setup_pll_blocking(
        pac.PLL_USB,
        xosc.operating_frequency(),
        hal::pll::common_configs::PLL_USB_48MHZ,
        &mut clocks,
        &mut pac.RESETS,
    )
    .map_err(|_x| false)
    .unwrap();
    // Step 6. Set the system to run from the PLLs we just configured.
    clocks
        .init_default(&xosc, &pll_sys, &pll_usb)
        .map_err(|_x| false)
        .unwrap();

    // The delay object lets us wait for specified amounts of time (in
    // milliseconds)
    let mut delay = cortex_m::delay::Delay::new(core.SYST, clocks.system_clock.freq().to_Hz());

    // The single-cycle I/O block controls our GPIO pins
    let sio = hal::Sio::new(pac.SIO);

    // Set the pins up according to their function on this particular board
    let pins = rp_pico::Pins::new(
        pac.IO_BANK0,
        pac.PADS_BANK0,
        sio.gpio_bank0,
        &mut pac.RESETS,
    );

    let spi_sclk: gpio::Pin<_, gpio::FunctionSpi, gpio::PullNone> = pins.gpio18.reconfigure();
    let spi_mosi: gpio::Pin<_, gpio::FunctionSpi, gpio::PullNone> = pins.gpio19.reconfigure();
    let spi_miso: gpio::Pin<_, gpio::FunctionSpi, gpio::PullUp> = pins.gpio16.reconfigure();
    let spi_cs = pins.gpio20.into_push_pull_output();

    // Create the SPI driver instance for the SPI0 device
    let spi = spi::Spi::<_, _, _, 8>::new(pac.SPI0, (spi_mosi, spi_miso, spi_sclk));

    let dc = pins.gpio22.into_push_pull_output();
    let rst = pins.gpio26.into_push_pull_output();

    // Exchange the uninitialised SPI driver for an initialised one
    let spi = spi.init(
        &mut pac.RESETS,
        clocks.peripheral_clock.freq(),
        RateExtU32::Hz(128_000_000),
        &embedded_hal::spi::MODE_0,
    );

    // Create a DisplayInterface from SPI and DC pin, with no manual CS control
    let di = SPIInterfaceNoCS::new(spi, dc);

    let mut disp = Builder::st7735s(di).with_display_size(180, 128).with_framebuffer_size(180, 128).with_invert_colors(mipidsi::ColorInversion::Normal).with_color_order(mipidsi::ColorOrder::Rgb).init(&mut delay, Some(rst)).unwrap();


    disp.set_orientation(Orientation::Landscape(true)).unwrap();
    disp.clear(Rgb565::BLACK).unwrap();

    let style = PrimitiveStyleBuilder::new()
        .stroke_color(Rgb565::RED)
        .stroke_width(2)
        .fill_color(Rgb565::GREEN)
        .build();

    let blank: PrimitiveStyle<Rgb565> = PrimitiveStyleBuilder::new()
        .fill_color(Rgb565::BLACK)
        .build();

    let mut player_c: CCanvasAt<Rgb565, 160, 128> = CCanvasAt::new(Point::new(10, 10));

    // Set the LED to be an output
    let mut led_pin = pins.b_power_save.into_push_pull_output();

    let mut input = Input {
        w: pins.gpio5.into_pull_up_input(),
        a: pins.gpio6.into_pull_up_input(),
        s: pins.gpio7.into_pull_up_input(),
        d: pins.gpio8.into_pull_up_input(),
        i: pins.gpio12.into_pull_up_input(),
        j: pins.gpio13.into_pull_up_input(),
        k: pins.gpio14.into_pull_up_input(),
        l: pins.gpio15.into_pull_up_input(),
    };

    let mut x = 16;
    let mut y = 16;

    led_pin.set_high().unwrap();

    player_c.draw(&mut disp).ok();

    loop {
        Rectangle::new(Point::new(0, 0), Size::new(32, 32))
            .into_styled(blank)
            .translate_mut(Point::new(x, y))
            .draw(&mut player_c)
            .ok();

        // Basic Movement
        if input.s.is_low().unwrap() {
            y += 2
        } else if input.d.is_low().unwrap() {
            x += 2
        } else if input.w.is_low().unwrap() {
            y -= 2
        } else if input.a.is_low().unwrap() {
            x -= 2
        }

        Rectangle::new(Point::new(0, 0), Size::new(32, 32))
            .into_styled(style)
            .translate_mut(Point::new(x, y))
            .draw(&mut player_c)
            .ok();
        player_c.draw(&mut disp).ok();
    }
}

// End of file
