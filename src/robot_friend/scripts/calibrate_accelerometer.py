"""Measure this robot's accelerometer offset and sensitivity, and save them.

Run it once per physical sensor — the numbers describe that part, not the code, which
is why they cannot be shipped in the repo. Afterwards ``AccelerometerFactory`` loads
them on its own and nothing has to be run again.

The sensor is on the Pi, so this is ``just pi::calibrate``.
"""
import argparse
from pathlib import Path

from robot_friend.exceptions.sensor_exception import SensorCalibrationException
from robot_friend.sensors.accelerometer.acceleration import GRAVITY_MS2
from robot_friend.sensors.accelerometer.accelerometer_factory import AccelerometerFactory
from robot_friend.sensors.accelerometer.backends.fake.fake_accelerometer import (
    FakeAccelerometer,
)
from robot_friend.sensors.accelerometer.calibration_store import save_calibration
from robot_friend.sensors.accelerometer.calibrator import (
    AccelerometerCalibrator,
    AccelerometerOrientation,
)
from robot_friend.sensors.calibration import IdentityCalibration


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--bus', type=int, default=1, help='I2C bus number')
    parser.add_argument(
        '--address', type=lambda value: int(value, 0), default=0x53,
        help='I2C address of the ADXL345 (0x53, or 0x1D with SDO high)',
    )
    parser.add_argument(
        '--samples', type=int, default=100,
        help='readings averaged per orientation',
    )
    parser.add_argument(
        '--output', type=Path, default=None,
        help='where to write the calibration (defaults to data/calibration/)',
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    # Measure against the bare sensor: a stored calibration must not be measured twice.
    accelerometer = AccelerometerFactory.get_accelerometer(
        bus=args.bus, address=args.address, calibration=IdentityCalibration()
    )
    if isinstance(accelerometer, FakeAccelerometer):
        raise SystemExit(
            'error: no accelerometer answering on this host, so there is nothing to '
            'calibrate.\n'
            '  the sensor is on the Pi: run `just pi::calibrate`\n'
            '  if you are on the Pi, check the wiring at '
            f'{args.address:#04x} on I2C bus {args.bus}'
        )

    with accelerometer:
        calibrator = AccelerometerCalibrator(accelerometer, samples=args.samples)
        print(f'Six placements, {args.samples} readings each. Hold the sensor still for each.\n')
        for orientation in AccelerometerOrientation:
            input(f'Place the sensor {orientation.value.instruction}, then press enter: ')
            mean = calibrator.record(orientation)
            print(f'  read x={mean.x:+7.2f}  y={mean.y:+7.2f}  z={mean.z:+7.2f}  m/s^2')

        try:
            calibration = calibrator.calibration()
        except SensorCalibrationException as exc:
            raise SystemExit(f'error: {exc}') from exc

        path = save_calibration(calibration, args.output)
        accelerometer.apply_calibration(calibration)
        check = accelerometer.read()

    print(f'\noffset (m/s^2): {_triple(calibration.offset)}')
    print(f'scale         : {_triple(calibration.scale)}')
    print(f'saved to      : {path}')
    print(f'check         : |a| = {check.magnitude:.3f} m/s^2 (gravity is {GRAVITY_MS2:.3f})')


def _triple(values: tuple[float, float, float]) -> str:
    return '  '.join(f'{axis}={value:+.4f}' for axis, value in zip('xyz', values))


if __name__ == '__main__':
    main()
