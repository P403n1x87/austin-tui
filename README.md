<p align="center">
  <br><img src="art/logo.png" alt="Austin TUI" /><br>
</p>

<h3 align="center">A Top-like Interface for Austin</h3>


<p align="center">
  <a href="https://github.com/P403n1x87/austin-tui/actions?workflow=Tests">
    <img src="https://github.com/P403n1x87/austin-tui/workflows/Tests/badge.svg"
         alt="GitHub Actions: Tests">
  </a>
  <br/>
  <!-- <a href="https://travis-ci.org/P403n1x87/austin-tui">
    <img src="https://travis-ci.org/P403n1x87/austin-tui.svg?branch=master"
         alt="Travis CI">
  </a>
  <a href="https://codecov.io/gh/P403n1x87/austin-tui">
    <img src="https://codecov.io/gh/P403n1x87/austin-tui/branch/master/graph/badge.svg"
         alt="Codecov">
  </a> -->
  <a href="https://pypi.org/project/austin-tui/">
    <img src="https://img.shields.io/pypi/v/austin-tui.svg"
         alt="PyPI">
  </a>
  <a href="https://pypi.org/project/austin-tui/">
    <img src="https://static.pepy.tech/personalized-badge/austin-tui?period=total&units=international_system&left_color=grey&right_color=blue&left_text=downloads"
         alt="PyPI Downloads">
  </a>
  &nbsp;
  <a href="https://anaconda.org/conda-forge/austin-tui">
    <img src="https://anaconda.org/conda-forge/austin-tui/badges/version.svg" />
  </a>
  <a href="https://anaconda.org/conda-forge/austin-tui">
    <img src="https://anaconda.org/conda-forge/austin-tui/badges/downloads.svg" />
  </a>
  
  <br/>
  
  <a href="https://github.com/P403n1x87/austin-tui/blob/master/LICENSE.md">
    <img src="https://img.shields.io/badge/license-GPLv3-ff69b4.svg"
         alt="LICENSE">
  </a>
</p>

<p align="center">
  <a href="#synopsis"><b>Synopsis</b></a>&nbsp;&bull;
  <a href="#installation"><b>Installation</b></a>&nbsp;&bull;
  <a href="#usage"><b>Usage</b></a>&nbsp;&bull;
  <a href="#compatibility"><b>Compatibility</b></a>&nbsp;&bull;
  <a href="#contribute"><b>Contribute</b></a>
</p>

<p align="center">
  <a
    href="https://www.buymeacoffee.com/Q9C1Hnm28"
    target="_blank">
  <img
    src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png"
    alt="Buy Me A Coffee" />
  </a>
</p>

# Synopsis

The Python TUI is a top-like text-based user interface for [Austin], the frame
stack sampler for CPython. Originally planned as a sample application to
showcase [Austin] uses, it's been promoted to a full-fledged project thanks to
great popularity.

<p align="center">
  <img src="art/austin-tui.gif"
       style="box-shadow: #111 0px 0px 16px;"
       alt="Austin TUI" />
</p>

The header shows you the information of the application that is being profiled,
like its PID, the command line used to invoke it, as well as a plot of the
amount of CPU and memory that is being used by it, in a system-monitor style.

To know more about how the TUI itself was made, have a read through [The Austin
TUI Way to Resourceful Text-based User Interfaces].

# Installation

Austin TUI can be installed directly from PyPI with

~~~ console
pipx install austin-tui
~~~

> **NOTE** In order for the TUI to work, the Austin 3 binary needs to be
> discoverable in the ways documented by the [austin-python] library. Have a
> look at [Austin installation] instructions to see how you can easily install
> Austin on your platform.

On macOS and Linux, Austin TUI and its dependencies (including Austin itself) 
can be installed via conda with

~~~ console
conda install -c conda-forge austin-tui
~~~

# Usage

Once [Austin] 3 and Austin TUI are installed, you can start using them
straight-away. If you want to launch and profile a Python script, say
`myscript.py`, you can do

~~~ console
austin-tui python3 myscript.py
~~~

or, if `myscript.py` is an executable script,

~~~ console
austin-tui ./myscript.py
~~~

Like [Austin], the TUI can also attach to a running Python application. To
analyse the frame stacks of all the processes of a running WSGI server, for
example, get hold of the PID of the parent process and do

~~~ console
sudo austin-tui -Cp <pid>
~~~

The `-C` option will instruct [Austin] to look for child Python processes, and you
will be able to navigate through them with the arrow keys.

> The TUI is based on `python-curses`. The version included with the standard
> Windows installations of Python is broken so it won't work out of the box. A
> solution is to install the the wheel of the port to Windows from
> [this](https://www.lfd.uci.edu/~gohlke/pythonlibs/#curses) page. Wheel files
> can be installed directly with `pip`, as described in the
> [linked](https://pip.pypa.io/en/latest/user_guide/#installing-from-wheels)
> page.

## Thread navigation

Profiling data is processed on a per-thread basis. The total number of threads
(across all processes, if sampling child processes) is displayed in the
top-right corner of the TUI. To navigate to a different thread, use the
<kbd>&larr;</kbd> and <kbd>&rarr;</kbd> arrows. The PID and TID of the currently
selected thread will appear in the middle of the top bar in the TUI.


## Full mode

By default, Austin TUI shows you statistics of the last seen stack for each
process and thread when the UI is refreshed (about every second). This is
similar to what top does with all the running processes on your system.

<p align="center">
  <img src="art/austin-tui-normal-mode.png"
       style="box-shadow: #111 0px 0px 16px;"
       alt="Austin TUI - Default mode" />
</p>

If you want to see all the collected statistics, with the frame stacks
represented as a rooted tree, you can press <kbd>F</kbd> to enter the _Full_
mode. The last seen stack will be highlighted so that you also have that
information available while in this mode.

<p align="center">
  <img src="art/austin-tui-full-mode.png"
       style="box-shadow: #111 0px 0px 16px;"
       alt="Austin TUI - Full mode" />
</p>

The information that gets displayed is very dynamic and could become tricky to
inspect. The current view can be paused by pressing <kbd>P</kbd>. To resume
refreshing the view, press <kbd>P</kbd> again. While the view is paused,
profiling data is still being captured and processed in the background, so that
when the view is resumed, the latest figures are shown.


## Graph mode

A live flame graph visualisation of the current thread statistics can be
displayed by pressing <kbd>G</kbd>. This might help with identifying the largest
frames at a glance.

<p align="center">
  <img src="art/austin-tui-flamegraph.gif"
       style="box-shadow: #111 0px 0px 16px;"
       alt="Austin TUI - Live flame graph" />
</p>

To toggle back to the top view, simply press <kbd>G</kbd> again.

## Save statistics

Peeking at a running Python application is nice but in many cases you would want
to save the collected data for further offline analysis (for example, you might
want to represent it as a flame graph). At any point, whenever you want to dump
the collected data to a file, you can press <kbd>S</kbd> and a file with all the
samples will be generated for you in the working directory, prefixed with
`austin_` and followed by a timestamp. The TUI will notify of the successful
operation on the bottom-right corner.

<p align="center">
  <img src="art/austin-tui-save.png"
       style="box-shadow: #111 0px 0px 16px;"
       alt="Austin TUI - Save notification" />
</p>

If you run the Austin TUI inside VS Code, you can benefit from the editor's
terminal features, like using <kbd>Ctrl</kbd>/<kbd>Cmd</kbd>+<kbd>Left-Click</kbd>
to hop straight into a source file at a given line. You can also leverage the
TUI's save feature to export the collected samples and import them into the
[Austin VS Code] extension to also get a flame graph representation.

<p align="center">
  <img src="art/austin-tui-vscode.gif"
       style="box-shadow: #111 0px 0px 16px;"
       alt="Austin TUI" />
</p>

## Threshold

The statistics reported by the TUI might be overwhelming, especially in full
mode. To reduce the amout of data that gets displayed, the keys <kbd>+</kbd> and
<kbd>-</kbd> can be used to increase or lower the `%TOTAL` threshold

<p align="center">
  <img src="art/austin-tui-threshold.png"
       style="box-shadow: #111 0px 0px 16px;"
       alt="Austin TUI - Threshold demonstration" />
</p>


# Compatibility

Austin TUI has been tested with Python 3.7-3.10 and is known to work on
**Linux**, **macOS** and **Windows**.

Since Austin TUI uses [Austin] to collect samples, the same note applies here:

> Due to the **System Integrity Protection** introduced in **macOS** with El
> Capitan, Austin cannot profile Python processes that use an executable located
> in the `/bin` folder, even with `sudo`. Hence, either run the interpreter from
> a virtual environment or use a Python interpreter that is installed in, e.g.,
> `/Applications` or via `brew` with the default prefix (`/usr/local`). Even in
> these cases, though, the use of `sudo` is required.

As for Linux users, the use of `sudo` can be avoided by granting Austin the
`cap_sys_ptrace` capability with, e.g.

~~~ console
sudo setcap cap_sys_ptrace+ep `which austin`
~~~

# Contribute

If you like Austin TUI and you find it useful, there are ways for you to
contribute.

If you want to help with the development, then have a look at the open issues
and have a look at the [contributing guidelines](CONTRIBUTING.md) before you
open a pull request.

You can also contribute to the development of the Austin TUI by becoming a
sponsor and/or by [buying me a coffee](https://www.buymeacoffee.com/Q9C1Hnm28)
on BMC or by chipping in a few pennies on
[PayPal.Me](https://www.paypal.me/gtornetta/1).

<p align="center">
  <a href="https://www.buymeacoffee.com/Q9C1Hnm28"
     target="_blank">
  <img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png"
       alt="Buy Me A Coffee" />
  </a>
</p>


[Austin]: https://github.com/P403n1x87/austin
[austin-python]: https://github.com/P403n1x87/austin-python#installation
[Austin installation]: https://github.com/P403n1x87/austin#installation
[Austin VS Code]: https://marketplace.visualstudio.com/items?itemName=p403n1x87.austin-vscode
[The Austin TUI Way to Resourceful Text-based User Interfaces]: https://p403n1x87.github.io/the-austin-tui-way-to-resourceful-text-based-user-interfaces.html
