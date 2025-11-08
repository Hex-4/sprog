#![no_std]
#![no_main]

use cortex_m::delay::Delay;
use embedded_graphics::{
    pixelcolor::Rgb565,
    prelude::*,
    primitives::Rectangle,
    style::PrimitiveStyleBuilder,
};
use embedded_hal::digital::v2::OutputPin;
use panic_halt as _;
use rp_pico::entry;
use embedded_hal::spi as spi_hal;
use rp_pico::hal::{fugit::RateExtU32, Clock};
use st7735_lcd::Orientation;

const MODE_0: spi_hal::Mode = spi_hal::Mode {
    polarity: spi_hal::Polarity::IdleHigh,
    phase: spi_hal::Phase::CaptureOnSecondTransition,
};

#[entry]
fn main() -> ! {
    let mut pac = rp_pico::pac::Peripherals::take().unwrap();
    let core = rp_pico::pac::CorePeripherals::take().unwrap();

    let mut watchdog = rp_pico::hal::Watchdog::new(pac.WATCHDOG);

    let clocks = rp_pico::hal::clocks::init_clocks_and_plls(
        rp_pico::XOSC_CRYSTAL_FREQ,
        pac.XOSC,
        pac.CLOCKS,
        pac.PLL_SYS,
        pac.PLL_USB,
        &mut pac.RESETS,
        &mut watchdog,
    )
    .ok()
    .unwrap();

    let mut delay = Delay::new(core.SYST, clocks.system_clock.freq().to_Hz());

    let sio = rp_pico::hal::Sio::new(pac.SIO);

    let pins = rp_pico::Pins::new(
        pac.IO_BANK0,
        pac.PADS_BANK0,
        sio.gpio_bank0,
        &mut pac.RESETS,
    );

    // SPI0 pins (default: SCK=GP18, RX=GP16, TX=GP19)
    let miso = pins.gpio16.into_function::<rp_pico::hal::gpio::FunctionSpi>();
    let mosi = pins.gpio19.into_function::<rp_pico::hal::gpio::FunctionSpi>();
    let sck = pins.gpio18.into_function::<rp_pico::hal::gpio::FunctionSpi>();

    // ST7735 pins
    let mut rst = pins.gpio26.into_push_pull_output();
    let dc = pins.gpio22.into_push_pull_output();
    let cs = pins.gpio20.into_push_pull_output();

    let spi_pins = (mosi, miso, sck);
    let spi: rp_pico::hal::Spi<_, _, _, 8> = rp_pico::hal::Spi::new(pac.SPI0, spi_pins);

    let spi = spi.init(
        &mut pac.RESETS,
        clocks.peripheral_clock.freq(),
        4_000_000u32.Hz(),
        MODE_0,
    );

    // Reset the display
    rst.set_low().unwrap();
    delay.delay_ms(10);
    rst.set_high().unwrap();
    delay.delay_ms(10);

    let mut disp = st7735_lcd::ST7735::new(spi, cs, dc, false, false, 128, 160);

    disp.init(&mut delay).unwrap();
    disp.set_orientation(&Orientation::Landscape).unwrap();

    let style = PrimitiveStyleBuilder::new()
        .fill_color(Rgb565::RED)
        .build();

    Rectangle::new(Point::new(0, 0), Point::new(127, 159))
        .into_styled(style)
        .draw(&mut disp)
        .unwrap();

    loop {}
}
