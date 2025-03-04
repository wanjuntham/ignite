from unittest.mock import patch

import pytest
import torch

from ignite.engine import Engine, Events
from ignite.handlers.state_param_scheduler import (
    ExpStateScheduler,
    LambdaStateScheduler,
    MultiStepStateScheduler,
    PiecewiseLinearStateScheduler,
    StepStateScheduler,
)

config1 = (3, [(2, 0), (5, 10)], True, [0.0, 0.0, 3.3333333333333335])
expected_hist2 = [0.0] * 10 + [float(i) for i in range(1, 11)] + [10.0] * 10
config2 = (30, [(10, 0), (20, 10)], True, expected_hist2)


@pytest.mark.parametrize(
    "max_epochs, milestones_values,  save_history, expected_param_history", [config1, config2],
)
def test_pwlinear_scheduler_linear_increase_history(
    max_epochs, milestones_values, save_history, expected_param_history
):
    # Testing linear increase
    engine = Engine(lambda e, b: None)
    pw_linear_step_parameter_scheduler = PiecewiseLinearStateScheduler(
        param_name="pwlinear_scheduled_param", milestones_values=milestones_values, save_history=save_history,
    )
    pw_linear_step_parameter_scheduler.attach(engine, Events.EPOCH_COMPLETED)
    engine.run([0] * 8, max_epochs=max_epochs)
    expected_param_history = expected_param_history
    assert hasattr(engine.state, "param_history")
    state_param = engine.state.param_history["pwlinear_scheduled_param"]
    assert len(state_param) == len(expected_param_history)
    assert state_param == expected_param_history

    state_dict = pw_linear_step_parameter_scheduler.state_dict()
    pw_linear_step_parameter_scheduler.load_state_dict(state_dict)


@pytest.mark.parametrize(
    "max_epochs, milestones_values", [(3, [(3, 12), (5, 10)]), (5, [(10, 12), (20, 10)]),],
)
def test_pwlinear_scheduler_step_constant(max_epochs, milestones_values):
    # Testing step_constant
    engine = Engine(lambda e, b: None)
    linear_state_parameter_scheduler = PiecewiseLinearStateScheduler(
        param_name="pwlinear_scheduled_param", milestones_values=milestones_values
    )
    linear_state_parameter_scheduler.attach(engine, Events.EPOCH_COMPLETED)
    engine.run([0] * 8, max_epochs=max_epochs)
    torch.testing.assert_allclose(getattr(engine.state, "pwlinear_scheduled_param"), milestones_values[0][1])

    state_dict = linear_state_parameter_scheduler.state_dict()
    linear_state_parameter_scheduler.load_state_dict(state_dict)


@pytest.mark.parametrize(
    "max_epochs, milestones_values, expected_val",
    [(2, [(0, 0), (3, 10)], 6.666666666666667), (10, [(0, 0), (20, 10)], 5.0),],
)
def test_pwlinear_scheduler_linear_increase(max_epochs, milestones_values, expected_val):
    # Testing linear increase
    engine = Engine(lambda e, b: None)
    linear_state_parameter_scheduler = PiecewiseLinearStateScheduler(
        param_name="pwlinear_scheduled_param", milestones_values=milestones_values
    )
    linear_state_parameter_scheduler.attach(engine, Events.EPOCH_COMPLETED)
    engine.run([0] * 8, max_epochs=max_epochs)
    torch.testing.assert_allclose(getattr(engine.state, "pwlinear_scheduled_param"), expected_val, atol=0.001, rtol=0.0)

    state_dict = linear_state_parameter_scheduler.state_dict()
    linear_state_parameter_scheduler.load_state_dict(state_dict)


@pytest.mark.parametrize(
    "max_epochs, milestones_values,", [(3, [(0, 0), (3, 10)]), (40, [(0, 0), (20, 10)])],
)
def test_pwlinear_scheduler_max_value(
    max_epochs, milestones_values,
):
    # Testing max_value
    engine = Engine(lambda e, b: None)
    linear_state_parameter_scheduler = PiecewiseLinearStateScheduler(
        param_name="linear_scheduled_param", milestones_values=milestones_values,
    )
    linear_state_parameter_scheduler.attach(engine, Events.EPOCH_COMPLETED)
    engine.run([0] * 8, max_epochs=max_epochs)
    torch.testing.assert_allclose(getattr(engine.state, "linear_scheduled_param"), milestones_values[-1][1])

    state_dict = linear_state_parameter_scheduler.state_dict()
    linear_state_parameter_scheduler.load_state_dict(state_dict)


def test_piecewiselinear_asserts():

    with pytest.raises(TypeError, match=r"Argument milestones_values should be a list or tuple"):
        PiecewiseLinearStateScheduler(param_name="linear_scheduled_param", milestones_values=None)

    with pytest.raises(ValueError, match=r"Argument milestones_values should be with at least one value"):
        PiecewiseLinearStateScheduler(param_name="linear_scheduled_param", milestones_values=[])

    with pytest.raises(ValueError, match=r"Argument milestones_values should be a list of pairs"):
        PiecewiseLinearStateScheduler(param_name="linear_scheduled_param", milestones_values=[(0.5,)])

    with pytest.raises(ValueError, match=r"Argument milestones_values should be a list of pairs"):
        PiecewiseLinearStateScheduler(param_name="linear_scheduled_param", milestones_values=[(10, 0.5), (0.6,)])

    with pytest.raises(ValueError, match=r"Milestones should be increasing integers"):
        PiecewiseLinearStateScheduler(param_name="linear_scheduled_param", milestones_values=[(10, 0.5), (5, 0.6)])

    with pytest.raises(TypeError, match=r"Value of a milestone should be integer"):
        PiecewiseLinearStateScheduler(param_name="linear_scheduled_param", milestones_values=[(0.5, 1)])


@pytest.mark.parametrize(
    "max_epochs, initial_value, gamma", [(3, 10, 0.99), (40, 5, 0.98)],
)
def test_exponential_scheduler(max_epochs, initial_value, gamma):
    engine = Engine(lambda e, b: None)
    exp_state_parameter_scheduler = ExpStateScheduler(
        param_name="exp_scheduled_param", initial_value=initial_value, gamma=gamma
    )
    exp_state_parameter_scheduler.attach(engine, Events.EPOCH_COMPLETED)
    engine.run([0] * 8, max_epochs=max_epochs)
    torch.testing.assert_allclose(getattr(engine.state, "exp_scheduled_param"), initial_value * gamma ** max_epochs)

    state_dict = exp_state_parameter_scheduler.state_dict()
    exp_state_parameter_scheduler.load_state_dict(state_dict)


@pytest.mark.parametrize(
    "max_epochs, initial_value, gamma, step_size", [(3, 10, 0.99, 5), (40, 5, 0.98, 22)],
)
def test_step_scheduler(
    max_epochs, initial_value, gamma, step_size,
):
    engine = Engine(lambda e, b: None)
    step_state_parameter_scheduler = StepStateScheduler(
        param_name="step_scheduled_param", initial_value=initial_value, gamma=gamma, step_size=step_size
    )
    step_state_parameter_scheduler.attach(engine, Events.EPOCH_COMPLETED)
    engine.run([0] * 8, max_epochs=max_epochs)
    torch.testing.assert_allclose(
        getattr(engine.state, "step_scheduled_param"), initial_value * gamma ** (max_epochs // step_size)
    )

    state_dict = step_state_parameter_scheduler.state_dict()
    step_state_parameter_scheduler.load_state_dict(state_dict)


from bisect import bisect_right


@pytest.mark.parametrize(
    "max_epochs, initial_value, gamma, milestones", [(3, 10, 0.99, [3, 6]), (40, 5, 0.98, [3, 6, 9, 10, 11])],
)
def test_multistep_scheduler(
    max_epochs, initial_value, gamma, milestones,
):
    engine = Engine(lambda e, b: None)
    multi_step_state_parameter_scheduler = MultiStepStateScheduler(
        param_name="multistep_scheduled_param", initial_value=initial_value, gamma=gamma, milestones=milestones,
    )
    multi_step_state_parameter_scheduler.attach(engine, Events.EPOCH_COMPLETED)
    engine.run([0] * 8, max_epochs=max_epochs)
    torch.testing.assert_allclose(
        getattr(engine.state, "multistep_scheduled_param"),
        initial_value * gamma ** bisect_right(milestones, max_epochs),
    )

    state_dict = multi_step_state_parameter_scheduler.state_dict()
    multi_step_state_parameter_scheduler.load_state_dict(state_dict)


def test_custom_scheduler():

    engine = Engine(lambda e, b: None)

    class LambdaState:
        def __init__(self, initial_value, gamma):
            self.initial_value = initial_value
            self.gamma = gamma

        def __call__(self, event_index):
            return self.initial_value * self.gamma ** (event_index % 9)

    lambda_state_parameter_scheduler = LambdaStateScheduler(
        param_name="custom_scheduled_param", lambda_obj=LambdaState(initial_value=10, gamma=0.99),
    )
    lambda_state_parameter_scheduler.attach(engine, Events.EPOCH_COMPLETED)
    engine.run([0] * 8, max_epochs=2)
    torch.testing.assert_allclose(
        getattr(engine.state, "custom_scheduled_param"), LambdaState(initial_value=10, gamma=0.99)(2)
    )
    engine.run([0] * 8, max_epochs=20)
    torch.testing.assert_allclose(
        getattr(engine.state, "custom_scheduled_param"), LambdaState(initial_value=10, gamma=0.99)(20)
    )

    state_dict = lambda_state_parameter_scheduler.state_dict()
    lambda_state_parameter_scheduler.load_state_dict(state_dict)


def test_custom_scheduler_asserts():
    class LambdaState:
        def __init__(self, initial_value, gamma):
            self.initial_value = initial_value
            self.gamma = gamma

    with pytest.raises(ValueError, match=r"Expected lambda_obj to be callable."):
        lambda_state_parameter_scheduler = LambdaStateScheduler(
            param_name="custom_scheduled_param", lambda_obj=LambdaState(initial_value=10, gamma=0.99),
        )


config1 = (
    PiecewiseLinearStateScheduler,
    {"param_name": "linear_scheduled_param", "milestones_values": [(3, 12), (5, 10)]},
)
config2 = (ExpStateScheduler, {"param_name": "exp_scheduled_param", "initial_value": 10, "gamma": 0.99})
config3 = (
    MultiStepStateScheduler,
    {"param_name": "multistep_scheduled_param", "initial_value": 10, "gamma": 0.99, "milestones": [3, 6]},
)


class LambdaState:
    def __init__(self, initial_value, gamma):
        self.initial_value = initial_value
        self.gamma = gamma

    def __call__(self, event_index):
        return self.initial_value * self.gamma ** (event_index % 9)


config4 = (
    LambdaStateScheduler,
    {"param_name": "custom_scheduled_param", "lambda_obj": LambdaState(initial_value=10, gamma=0.99)},
)


@pytest.mark.parametrize("scheduler_cls,scheduler_kwargs", [config1, config2, config3, config4])
def test_simulate_and_plot_values(scheduler_cls, scheduler_kwargs):

    import matplotlib

    matplotlib.use("Agg")

    def _test(scheduler_cls, scheduler_kwargs):
        event = Events.EPOCH_COMPLETED
        max_epochs = 2
        data = [0] * 10

        scheduler = scheduler_cls(**scheduler_kwargs)
        trainer = Engine(lambda engine, batch: None)
        scheduler.attach(trainer, event)
        trainer.run(data, max_epochs=max_epochs)

        # launch plot values
        scheduler_cls.plot_values(num_events=len(data) * max_epochs, **scheduler_kwargs)

    _test(scheduler_cls, scheduler_kwargs)


@pytest.mark.parametrize("scheduler_cls,scheduler_kwargs", [config1, config2, config3, config4])
def test_state_param_asserts(scheduler_cls, scheduler_kwargs):
    import re

    def _test(scheduler_cls, scheduler_kwargs):
        scheduler = scheduler_cls(**scheduler_kwargs)
        with pytest.raises(
            ValueError,
            match=r"Attribute: '"
            + re.escape(scheduler_kwargs["param_name"])
            + "' is already defined in the Engine.state.This may be a conflict between multiple StateParameterScheduler"
            + " handlers.Please choose another name.",
        ):

            trainer = Engine(lambda engine, batch: None)
            event = Events.EPOCH_COMPLETED
            max_epochs = 2
            data = [0] * 10
            scheduler.attach(trainer, event)
            trainer.run(data, max_epochs=max_epochs)
            scheduler.attach(trainer, event)

    _test(scheduler_cls, scheduler_kwargs)


def test_torch_save_load():

    lambda_state_parameter_scheduler = LambdaStateScheduler(
        param_name="custom_scheduled_param", lambda_obj=LambdaState(initial_value=10, gamma=0.99),
    )

    torch.save(lambda_state_parameter_scheduler, "dummy_lambda_state_parameter_scheduler.pt")
    loaded_lambda_state_parameter_scheduler = torch.load("dummy_lambda_state_parameter_scheduler.pt")

    engine1 = Engine(lambda e, b: None)
    lambda_state_parameter_scheduler.attach(engine1, Events.EPOCH_COMPLETED)
    engine1.run([0] * 8, max_epochs=2)
    torch.testing.assert_allclose(
        getattr(engine1.state, "custom_scheduled_param"), LambdaState(initial_value=10, gamma=0.99)(2)
    )

    engine2 = Engine(lambda e, b: None)
    loaded_lambda_state_parameter_scheduler.attach(engine2, Events.EPOCH_COMPLETED)
    engine2.run([0] * 8, max_epochs=2)
    torch.testing.assert_allclose(
        getattr(engine2.state, "custom_scheduled_param"), LambdaState(initial_value=10, gamma=0.99)(2)
    )

    torch.testing.assert_allclose(
        getattr(engine1.state, "custom_scheduled_param"), getattr(engine2.state, "custom_scheduled_param")
    )


def test_simulate_and_plot_values_no_matplotlib():
    def _test(scheduler_cls, **scheduler_kwargs):
        event = Events.EPOCH_COMPLETED
        max_epochs = 2
        data = [0] * 10

        scheduler = scheduler_cls(**scheduler_kwargs)
        trainer = Engine(lambda engine, batch: None)
        scheduler.attach(trainer, event)
        trainer.run(data, max_epochs=max_epochs)

        # launch plot values
        scheduler_cls.plot_values(num_events=len(data) * max_epochs, **scheduler_kwargs)

    with pytest.raises(RuntimeError, match=r"This method requires matplotlib to be installed."):
        with patch.dict("sys.modules", {"matplotlib.pyplot": None}):
            _test(
                MultiStepStateScheduler,
                param_name="multistep_scheduled_param",
                initial_value=10,
                gamma=0.99,
                milestones=[3, 6],
            )


def test_docstring_examples():
    # LambdaStateScheduler

    engine = Engine(lambda e, b: None)

    class LambdaState:
        def __init__(self, initial_value, gamma):
            self.initial_value = initial_value
            self.gamma = gamma

        def __call__(self, event_index):
            return self.initial_value * self.gamma ** (event_index % 9)

    param_scheduler = LambdaStateScheduler(param_name="param", lambda_obj=LambdaState(10, 0.99),)

    param_scheduler.attach(engine, Events.EPOCH_COMPLETED)

    engine.run([0] * 8, max_epochs=2)

    # PiecewiseLinearStateScheduler

    engine = Engine(lambda e, b: None)

    param_scheduler = PiecewiseLinearStateScheduler(
        param_name="param", milestones_values=[(10, 0.5), (20, 0.45), (21, 0.3), (30, 0.1), (40, 0.1)]
    )

    param_scheduler.attach(engine, Events.EPOCH_COMPLETED)

    engine.run([0] * 8, max_epochs=40)

    # ExpStateScheduler

    engine = Engine(lambda e, b: None)

    param_scheduler = ExpStateScheduler(param_name="param", initial_value=10, gamma=0.99)

    param_scheduler.attach(engine, Events.EPOCH_COMPLETED)

    engine.run([0] * 8, max_epochs=2)

    # StepStateScheduler

    engine = Engine(lambda e, b: None)

    param_scheduler = StepStateScheduler(param_name="param", initial_value=10, gamma=0.99, step_size=5)

    param_scheduler.attach(engine, Events.EPOCH_COMPLETED)

    engine.run([0] * 8, max_epochs=10)

    # MultiStepStateScheduler

    engine = Engine(lambda e, b: None)

    param_scheduler = MultiStepStateScheduler(param_name="param", initial_value=10, gamma=0.99, milestones=[3, 6],)

    param_scheduler.attach(engine, Events.EPOCH_COMPLETED)

    engine.run([0] * 8, max_epochs=10)
