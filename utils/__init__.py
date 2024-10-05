#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2023 Théo Morales <theo.morales.fr@gmail.com>
#
# Distributed under terms of the MIT license.


# import importlib
# import inspect
import os
import random

# import sys
import traceback
from typing import Any, Callable, Dict, List, Optional

# import IPython
import numpy as np
import torch
from hydra.utils import to_absolute_path
from torch import Tensor, nn

from conf import project as project_conf


def load_model_ckpt(load_from: Optional[str], training_mode: bool) -> Optional[str]:
    model_ckpt_path = None
    if load_from is not None:
        if load_from.endswith(".ckpt"):
            model_ckpt_path = to_absolute_path(load_from)
            if not os.path.exists(model_ckpt_path):
                raise ValueError(f"File {model_ckpt_path} does not exist!")
        else:
            run_models = sorted(
                [
                    f
                    for f in os.listdir(to_absolute_path(f"runs/{load_from}/"))
                    if f.endswith(".ckpt")
                    and (not f.startswith("last") if not training_mode else True)
                ]
            )
            if len(run_models) < 1:
                raise ValueError(f"No model found in runs/{load_from}/")
            model_ckpt_path = to_absolute_path(
                os.path.join(
                    "runs",
                    load_from,
                    run_models[-1],
                )
            )
    return model_ckpt_path


def seed_everything(seed: int):
    torch.manual_seed(seed)  # type: ignore
    np.random.seed(seed)
    random.seed(seed)
    # torch.use_deterministic_algorithms(True)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        # torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def to_cuda_(x: Any) -> Any:
    device = "cpu"
    dtype = x.dtype if isinstance(x, Tensor) else None
    if project_conf.USE_CUDA_IF_AVAILABLE and torch.cuda.is_available():
        device = "cuda"
    elif project_conf.USE_MPS_IF_AVAILABLE and torch.backends.mps.is_available():
        device = "mps"
        dtype = torch.float32 if dtype is torch.float64 else dtype
    else:
        return x
    if isinstance(x, (Tensor, nn.Module)):
        x = x.to(device, dtype=dtype)
    elif isinstance(x, tuple):
        x = tuple(to_cuda_(t) for t in x)  # type: ignore
    elif isinstance(x, list):
        x = [to_cuda_(t) for t in x]  # type: ignore
    elif isinstance(x, dict):
        x = {key: to_cuda_(value) for key, value in x.items()}  # type: ignore
    return x


def to_cuda(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to move function arguments to cuda if available and if they are
    torch tensors, torch modules or tuples/lists of."""

    def wrapper(*args: List[Any], **kwargs: Dict[str, Any]) -> Any:
        args = to_cuda_(args)
        for key, value in kwargs.items():
            kwargs[key] = to_cuda_(value)
        return func(*args, **kwargs)

    return wrapper


# def blink_pbar(i: int, pbar: tqdm, n: int) -> None:
#     """Blink the progress bar every n iterations.
#     Args:
#         i (int): current iteration
#         pbar (tqdm): progress bar
#         n (int): blink every n iterations
#     """
#     if i % n == 0:
#         pbar.colour = (
#             project_conf.Theme.TRAINING.value
#             if pbar.colour == project_conf.Theme.VALIDATION.value
#             else project_conf.Theme.VALIDATION.value
#         )
#
#
# def update_pbar_str(pbar: tqdm, string: str, color_code: int) -> None:
#     """Update the progress bar string.
#     Args:
#         pbar (tqdm): progress bar
#         string (str): string to update the progress bar with
#         color_code (int): color code for the string
#     """
#     pbar.set_description_str(colorize(string, color_code))


def get_function_frame(func, exc_traceback):
    """
    Find the frame of the original function in the traceback.
    """
    for frame, _ in traceback.walk_tb(exc_traceback):
        if frame.f_code.co_name == func.__name__:
            return frame
    return None


'''
# TODO: Refactor this
def debug_trace(callable):
    """
    Decorator to call a callable and launch an IPython shell after an exception is thrown. This
    lets the user debug the callable in the context of the exception and fix the function/method. It will
    then retry the call until no exception is thrown, after reloading the function/method code.
    """

    def wrapper(*args, **kwargs):
        nonlocal callable
        while True:
            try:
                return callable(*args, **kwargs)
            except Exception as exception:
                # If the exception came from the wrapper itself, we should not catch it!
                exc_type, exc_value, exc_traceback = sys.exc_info()
                if exc_traceback.tb_next is None:
                    traceback.print_exc()
                    sys.exit(1)
                elif exc_traceback.tb_next.tb_frame.f_code.co_name == "wrapper":
                    print(
                        colorize(
                            f"[!] Caught exception in 'debug_trace': {exception}",
                            project_conf.ANSI_COLORS["red"],
                        )
                    )
                    sys.exit(1)
                print(
                    colorize(
                        f"[!] Caught exception: {exception}",
                        project_conf.ANSI_COLORS["red"],
                    )
                )
                full_traceback = input(
                    colorize(
                        "[?] Display full traceback? (y/[N]) ",
                        project_conf.ANSI_COLORS["yellow"],
                    )
                )
                if full_traceback.lower() == "y":
                    traceback.print_exc()
                reload = input(
                    colorize(
                        "[?] Take action? ([L]aunch IPython shell and reload the code/[r]eload the code/[a]bort) ",
                        project_conf.ANSI_COLORS["yellow"],
                    )
                )

                if reload.lower() not in ("l", "", "r"):
                    print("[!] Aborting")
                    # TODO: Why can't I just raise the exception? It's weird but it gets caught by
                    # the wrapper a few times until it finally gets raised.
                    sys.exit(1)
                if reload.lower() in ("l", ""):
                    # Drop into an IPython shell to inspect the callable and its context.
                    # Get the frame of the original callable
                    frame = get_function_frame(callable, exc_traceback)
                    if not frame:
                        raise Exception(
                            f"Could not find the frame of the original function {callable} in the traceback."
                        )
                    interactive_shell = IPython.terminal.embed.InteractiveShellEmbed(
                        cfg=IPython.terminal.embed.load_default_config(),
                        banner1=colorize(
                            f"[*] Dropping into an IPython shell to inspect {callable} "
                            + "with the locals as they were at the time of the exception "
                            + f"thrown at line {frame.f_lineno} of {frame.f_code.co_filename}."
                            + "\n============================== TIPS =============================="
                            + "\n -> Use '%whos' to list variables in the current scope."
                            + "\n -> Use '%debug' to launch the debugger."
                            + "\n -> Use '<variable_name>' to display the value of a variable. "
                            + "Add a '?' to display the type."
                            + "\n -> Use '<function_name>?' to display the function's docstring. "
                            + "Add a '?' to display the source code."
                            + "\n -> Use 'frame??' to display the source code of the current frame which threw the exception."
                            + "\n==================================================================",
                            project_conf.ANSI_COLORS["green"],
                        ),
                        exit_msg=colorize(
                            "Leaving IPython shell.", project_conf.ANSI_COLORS["yellow"]
                        ),
                    )
                    interactive_shell(local_ns={**frame.f_locals, "frame": frame})
                # I think it's not a good idea to let the user reload other modules, because it could
                # lead to unexpected behavior across the codebase (e.g. if the function called by the
                # callable is used elsewhere where the reference to the function is not updated,
                # which probably do not want to do).
                print(
                    colorize(
                        f"[*] Reloading callable {callable.__name__}.",
                        project_conf.ANSI_COLORS["green"],
                    )
                    + colorize(
                        " (Anything outside this scope will not be reloaded)",
                        project_conf.ANSI_COLORS["red"],
                    )
                )

                # This is super interesting stuff about Python's inner workings! Look at the
                # documentation for more information:
                # https://docs.python.org/3/reference/datamodel.html?highlight=__func__#instance-methods
                importlib.reload(sys.modules[callable.__module__])
                reloaded_module = importlib.import_module(callable.__module__)
                rld_callable = None
                if hasattr(callable, "__self__"):
                    # callable is a *bound* class method, so we can retrieve the class and reload it
                    print(
                        colorize(
                            f"-> Reloading class {callable.__self__.__class__.__name__}",
                            project_conf.ANSI_COLORS["cyan"],
                        )
                    )
                    reloaded_class = getattr(
                        reloaded_module, callable.__self__.__class__.__name__
                    )
                    # Now find the method in the reloaded class, and replace the
                    # with the reloaded one.
                    for name, val in inspect.getmembers(reloaded_class):
                        if (
                            inspect.isfunction(val)
                            and val.__name__ == callable.__name__
                        ):
                            print(
                                colorize(
                                    f"-> Reloading method {name}",
                                    project_conf.ANSI_COLORS["cyan"],
                                )
                            )
                            rld_callable = val
                else:
                    # Most likely we end up here because callable is the function object of the
                    # called method, not the method itself. Is there even a case where we end up
                    # with the method object? First we can try to reload it directly if it was a
                    # module level function:
                    try:
                        print(
                            colorize(
                                f"-> Reloading module level function {callable.__name__}",
                                project_conf.ANSI_COLORS["cyan"],
                            )
                        )
                        callable = getattr(reloaded_module, callable.__name__)
                    except AttributeError:
                        print(
                            colorize(
                                f"-> Could not find {callable.__name__} in module {callable.__module__}. "
                                + "Looking for a class method...",
                                project_conf.ANSI_COLORS["magenta"],
                            )
                        )
                        # Ok that failed, so we need to find the class of the method and reload it,
                        # then find the method in the reloaded class and replace the function with
                        # the method's function object; this is the same as above.
                        # TODO: This feels very hacky! Can we find the class in a better way, maybe
                        # without going through all classes in the module? Because I'm not sure if the
                        # qualname always contains the class name in this way; like what about
                        # inheritance?
                        print(
                            colorize(
                                f"-> Reloading class {callable.__qualname__.split('.')[0]}",
                                project_conf.ANSI_COLORS["cyan"],
                            )
                        )
                        reloaded_class = getattr(
                            reloaded_module, callable.__qualname__.split(".")[0]
                        )
                        for name, val in inspect.getmembers(reloaded_class):
                            if inspect.isfunction(val) and name == callable.__name__:
                                print(
                                    colorize(
                                        f"-> Reloading method {name}",
                                        project_conf.ANSI_COLORS["cyan"],
                                    )
                                )
                                rld_callable = val
                                break
                if rld_callable is None:
                    print(
                        colorize(
                            f"[!] Could not reload callable {callable}!",
                            project_conf.ANSI_COLORS["red"],
                        )
                    )
                    sys.exit(1)
                print(
                    colorize(
                        f"[*] Reloaded callable {callable.__name__}! Retrying the call...",
                        project_conf.ANSI_COLORS["green"],
                    )
                )
                callable = rld_callable
                # TODO: What if the user modified other methods/functions called by the callable?
                # Should we find them and recursively reload them? Maybe we can keep track of
                # every called *user* function, and if the user modifies any after an exception is
                # caught, we can first ask if we should reload it, warning them about the previous
                # calls that will be affected by the reload.
                # TODO: Check if we changed the function signature and if so, backtrace the call
                # and update the arguments by re-running the routine that generated them and made
                # the call.
                # TODO: Free memory allocation (open file descriptors, etc.) before retrying the
                # call.

    return wrapper


def debug_methods(cls):
    """
    Decorator to debug all methods of a class using the debug_trace decorator if the DEBUG environment variable is set.
    """
    if not project_conf.DEBUG:
        return cls
    for key, val in vars(cls).items():
        if callable(val):
            setattr(cls, key, debug_trace(val))
    return cls


class DebugMetaclass(type):
    """
    We can use this metaclass to automatically decorate all methods of a class with the debug_trace
    decorator, making it simpler with inheritance.
    """

    def __new__(cls, name, bases, dct):
        obj = super().__new__(cls, name, bases, dct)
        obj = debug_methods(obj)
        return obj
'''
