<p align="center">
  <br>
  <img src="art/logo.png" alt="Austin TUI">
  <br>
</p>



The Python TUI that is currently included in this repository provides an
example of how to use Austin to profile Python applications. You can use
`PageUp` and `PageDown` to navigate the frame stack of each frame as the Python
application runs.

If you want to give it a go you can install it using `pip` with

~~~ bash
pip install git+https://github.com/P403n1x87/austin.git --upgrade
~~~

and run it with

~~~ bash
austin-tui [OPTION...] command [ARG...]
~~~

with the same command line as Austin.

> The TUI is based on `python-curses`. The version included with the standard
> Windows installations of Python is broken so it won't work out of the box. A
> solution is to install the the wheel of the port to Windows from
> [this](https://www.lfd.uci.edu/~gohlke/pythonlibs/#curses) page. Wheel files
> can be installed directly with `pip`, as described in the
> [linked](https://pip.pypa.io/en/latest/user_guide/#installing-from-wheels)
> page.

<!-- ![austin-tui thread navigation](art/austin-tui_threads_nav.gif) -->
<p align="center"><img src="art/austin-tui_threads_nav.gif" style="box-shadow: #111 0px 0px 16px;"/></p>
