# Better Window Names for tmux

A plugin to name your tmux windows smartly, like IDE's.

![Tmux Window Name Screenshot](screenshots/example.png)

## Index
* [Use case](#use-case)
* [Usage](#usage)
* [How it works](#how-it-works)
* [Installation](#installation)
* [Configuration Options](#configuration-options)

## Dependencies

* tmux (Tested on 3.0a)
* Python 3.9+
* pip
* [libtmux](https://github.com/tmux-python/libtmux) >=0.31.0

## Use case

If you are using tmux as your main multiplexer you probably found yourself with 5+ windows per session with indexed names but no information about whats going on in the windows.

You tried to configure `automatic-rename` and `automatic-rename-format` but you found yourself pretty limited.

This plugin comes to solve those issues to name your windows inspired by IDE tablines.\
It makes sure to show you the shortest path possible!

#### Examples
This session:
```
1. ~/workspace/my_project
2. ~/workspace/my_project/tests/
3. ~/workspace/my_other_project
4. ~/workspace/my_other_project/tests
```
Will display:
```
1. my_project
2. my_project/tests
3. my_other_project
4. my_other_project/tests
```

---

It knows which programs runs
```
1. ~/workspace/my_project (with nvim)
2. ~/workspace/my_project
3. ~/workspace/my_other_project (with git diff)
4. ~/workspace/my_other_project
```
Will display:
```
1. nvim:my_project
2. my_project
3. git diff:my_other_project
4. my_other_project
```

For more scenarios you check out the [tests](tests/test_exclusive_paths.py).

## Usage
[Install](#installation) the plugin and let it name your windows :)

_**Note**_: if you are using [tmux-resurrect](https://github.com/tmux-plugins/tmux-resurrect) `tmux-window-name` must be loaded before `tmux-resurrect`

You can `tmux rename-window` manually to set your own window names, to re-enable automatic renames set run `tmux rename-window ""`

Make sure your configuration/other plugins doesn't turn on `automatic-rename` and doesn't rename your windows.

### Automatic rename after launching neovim
By default `tmux-window-name` hooks `after-select-window` which trigged when switching windows.

You can add autocmd to rename after nvim launches and stops as so:
```lua
local uv = vim.uv

vim.api.nvim_create_autocmd({ 'VimEnter', 'VimLeave' }, {
	callback = function()
		if vim.env.TMUX_PLUGIN_MANAGER_PATH then
			uv.spawn(vim.env.TMUX_PLUGIN_MANAGER_PATH .. '/tmux-window-name/scripts/rename_session_windows.py', {})
		end
	end,
})
```

### Automatic rename after changing dir
By default `tmux-window-name` hooks `after-select-window` which trigged when switching windows, you can add hook in your `.shellrc` to execute `tmux-window-name`
##### .zshrc
```bash
tmux-window-name() {
	($TMUX_PLUGIN_MANAGER_PATH/tmux-window-name/scripts/rename_session_windows.py &)
}

add-zsh-hook chpwd tmux-window-name
```

#### Hooks Used
Make sure the hooks that used aren't overridden.
* @resurrect-hook-pre-restore-all
* @resurrect-hook-post-restore-all

---

## How it works
Each time you unfocus from a pane, the plugin looks for every active pane in your session windows.

_**Note**_: if you have a better hook in mind make sure to notify me!

1. If shell is running, it shows the current dir as short as possible, `long_dir/a` -> `a`, it avoids [intersections](#Intersections) too!
1. If "regular" program is running it shows the program with the args, `less ~/my_file` -> `less ~/my_file`.
1. If "special" program is running it shows the program with the dir attached, `git diff` (in `long_dir/a`) -> `git diff:a`, it avoids [intersections](#Intersections) too!

### Intersections

To make the shortest path as possible the plugin finds the shortest not common path if your windows.

---

## Installation

### Prerequisites

First, you need to install the Python dependency `libtmux` (>=0.31.0). Choose one of the following methods based on your preference:

**Important:** Verify your Python version first:
```sh
python3 --version  # Should be 3.9 or higher
which python3      # Check which Python tmux will use
```

#### Option 1: Using pipx (Recommended for isolated installation)
[pipx](https://pypa.github.io/pipx/) installs Python applications in isolated environments, preventing dependency conflicts.

```sh
# Install pipx if you haven't already
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install libtmux using pipx
pipx install libtmux
```

#### Option 2: Using pip with --user flag
Install to your user's Python directory without requiring sudo:

```sh
python3 -m pip install --user libtmux
```

#### Option 3: Using system package manager
Some distributions provide libtmux as a package:

```sh
# On Arch Linux/Manjaro
sudo pacman -S python-libtmux

# On Fedora
sudo dnf install python3-libtmux

# On macOS with Homebrew (after installing python)
pip3 install libtmux
```

#### Option 4: Using virtual environment
For development or testing in an isolated environment:

```sh
# Create virtual environment
python3 -m venv ~/.tmux-venv

# Activate it
source ~/.tmux-venv/bin/activate

# Install libtmux
pip install libtmux

# Add to your shell RC file to auto-activate
echo 'source ~/.tmux-venv/bin/activate' >> ~/.bashrc  # or ~/.zshrc
```

### Plugin Installation

After installing the Python dependencies, install the tmux plugin itself:

#### Installation with [Tmux Plugin Manager](https://github.com/tmux-plugins/tpm) (recommended)

Add plugin to the list of TPM plugins:

```tmux.conf
set -g @plugin 'ofirgall/tmux-window-name'
```

_**Note**_: set `tmux-window-name` before `tmux-resurrect` (if you are using `tmux-resurrect`)

```tmux.conf
set -g @plugin 'ofirgall/tmux-window-name'
set -g @plugin 'tmux-plugins/tmux-resurrect'
```

Press prefix + I to install it.

#### Manual Installation

Clone the repo:

```bash
git clone https://github.com/ofirgall/tmux-window-name.git ~/clone/path
```

Add this line to your .tmux.conf:

```tmux.conf
run-shell ~/clone/path/tmux_window_name.tmux
```

Reload TMUX environment with:

```bash
tmux source-file ~/.tmux.conf
```

### Troubleshooting

#### Common Issues and Solutions

##### 1. "Python dependency libtmux not found"
This error means libtmux is not installed or not accessible to tmux.

**Solution:**
- Verify libtmux is installed: `python3 -c "import libtmux; print(libtmux.__version__)"`
- Make sure you're using the same Python that tmux uses
- If using pipx, ensure the pipx bin directory is in your PATH
- If using virtual environment, ensure it's activated before starting tmux

##### 2. Script fails with fish shell
If windows aren't being renamed properly when using fish shell:

**Solution:**
- Update to the latest version of the plugin (this issue has been fixed)
- The plugin now handles login shells with dash prefix (e.g., `-fish`)

##### 3. Windows not being renamed
Check if the plugin is properly enabled:

```bash
# Check if hooks are set
tmux show-hooks -g | grep tmux-window-name

# Check if the script is executable
ls -la ~/.tmux/plugins/tmux-window-name/scripts/rename_session_windows.py

# Check logs for errors (if debug mode is enabled)
tail -f /tmp/tmux-window-name.log
```

##### 4. Permission denied errors
If you get permission errors when running the script:

**Solution:**
```bash
# Make the script executable
chmod +x ~/.tmux/plugins/tmux-window-name/scripts/rename_session_windows.py
chmod +x ~/.tmux/plugins/tmux-window-name/tmux_window_name.tmux
```

##### 5. Using with pyenv or other Python version managers
If you use pyenv, rbenv, or similar tools, ensure tmux can find the correct Python:

**Solution:**
Add to your `.tmux.conf` before loading the plugin:
```tmux.conf
# For pyenv
set-environment -g PATH "$HOME/.pyenv/shims:$PATH"

# For a specific Python path
set-environment -g PYTHON_PATH "/usr/local/bin/python3"
```

## Configuration Options
_**Note**_: Options are parsed using safe evaluation methods (`ast.literal_eval` and `json.loads`) to prevent code injection. Complex Python expressions are supported for list and dictionary options.

### `@tmux_window_name_shells`

Shell programs, will show dir instead of the program

```tmux.conf
set -g @tmux_window_name_shells "['bash', 'fish', 'sh', 'zsh']"
```

### `@tmux_window_name_dir_programs`

Programs that will show the dir name too.

E.g: `git diff` running in `long_dir/my_repo` will show `git diff:my_repo`

```tmux.conf
set -g @tmux_window_dir_programs "['nvim', 'vim', 'vi', 'git']"
```

### `@tmux_window_name_ignored_programs`

Programs that will be skipped/ignored when looking for active program.

```tmux.conf
set -g @tmux_window_name_ignored_programs "['sqlite3']" # Default is []
```

### `@tmux_window_name_max_name_len`

Maximum name length of a window

```tmux.conf
set -g @tmux_window_name_max_name_len "20"
```

### `@tmux_window_name_use_tilde`

Replace `$HOME` with `~` in window names

```tmux.conf
set -g @tmux_window_name_use_tilde "False"
```

### `@tmux_window_name_show_program_args`

Show arguments that the program has been ran with.

```tmux.conf
set -g @tmux_window_name_show_program_args "True"
```

### `@tmux_window_name_substitute_sets`

Replace program command lines with [re.sub](https://docs.python.org/3/library/re.html#re.sub). \
The options expect list of tuples with 2 elements, `pattern` and `repl`. \
E.g: The example below will replace `/usr/bin/python3 /usr/bin/ipython3` with `ipython3`, and the same for ipython2

Note: use `~/.tmux/plugins/tmux-window-name/scripts/rename_session_windows.py --print_programs` to see the full program command line and the results of the substitute.

```tmux.conf
set -g @tmux_window_name_substitute_sets "[('.+ipython2', 'ipython2'), ('.+ipython3', 'ipython3')]"

# Same example but with regex groups
set -g @tmux_window_name_substitute_sets "[('.+ipython([32])', 'ipython\g<1>')]"

# Default Value:
set -g @tmux_window_name_substitute_sets "[('.+ipython([32])', 'ipython\g<1>'), ('^(/usr)?/bin/(.+)', '\g<2>'), ('(bash) (.+)/(.+[ $])(.+)', '\g<3>\g<4>'), ('.+poetry shell', 'poetry')]"
	# 0: from example
	# 1: removing `/usr/bin` and `/bin` prefixes of files
	# 2: removing `bash /long/path/for/bashscript`
	# 3: changing "poetry shell" to "poetry"
```

### `@tmux_window_name_dir_substitute_sets`

Replace dir lines with [re.sub](https://docs.python.org/3/library/re.html#re.sub). \
The options expect list of tuples with 2 elements, `pattern` and `repl` as above.
E.g: The example below will replace `tmux-resurrect` with `resurrect`

```tmux.conf
set -g @tmux_window_name_dir_substitute_sets "[('tmux-(.+)', '\\g<1>')]"

# Default Value:
set -g @tmux_window_name_dir_substitute_sets "[]"
```

### `@tmux_window_name_icon_style`

Configure how icons are displayed in window names. \
Available styles:
- `name`: Show only program name (default)
- `icon`: Show only icon
- `name_and_icon`: Show both icon and program name

```tmux.conf
# Show only icons
set -g @tmux_window_name_icon_style "'icon'"

# Show icons with program names
set -g @tmux_window_name_icon_style "'name_and_icon'"

# Default Value:
set -g @tmux_window_name_icon_style "'name'"
```

### `@tmux_window_name_custom_icons`

Customize icons for specific programs. \
The value should be a dictionary mapping program names to their icons.

```tmux.conf
# Custom icons example
set -g @tmux_window_name_custom_icons '{"python": "🐍", "custom_app": "📦"}'

# Default Value:
set -g @tmux_window_name_custom_icons '{}'
```

_**Note**_: Icons can be any Unicode characters, including emoji or Nerd Font icons. \
If using Nerd Font icons, make sure your terminal supports them.

---

## Debug Configuration Options

### `@tmux_window_name_log_level`

Set log level of the script. \
Logs output go to `/tmp/tmux-window-name.log`

```tmux.conf
# Enable debug logs
set -g @tmux_window_name_log_level "'DEBUG'"

# Default Value:
set -g @tmux_window_name_log_level "'WARNING'"
```

---

# Development

## Setting up the development environment

1. Clone the repository:
```bash
git clone https://github.com/ofirgall/tmux-window-name.git
cd tmux-window-name
```

2. Install [uv](https://github.com/astral-sh/uv) if you haven't already (one-time):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or: brew install uv
```

3. Sync development dependencies (creates/updates `.venv`):
```bash
make install
```

For better IDE support, you may also want to:
```bash
# Add scripts to PYTHONPATH for your shell session
export PYTHONPATH="${PYTHONPATH}:$(pwd)/scripts"

# Or for IDE configuration, see the pyrightconfig.json and .vscode/settings.json files
```

4. Install pre-commit hooks:
```bash
make precommit-install
```

## Pre-commit hooks

This project uses [pre-commit](https://pre-commit.com/) to maintain code quality. The hooks will run automatically before each commit.

### Included hooks:
- **ruff**: Python formatting and linting
- **mypy**: Type checking
- **bandit**: Security vulnerability scanning
- **shellcheck**: Shell script linting
- **markdownlint**: Markdown formatting
- **yamllint**: YAML validation
- Various general checks (trailing whitespace, merge conflicts, large files, etc.)

### Manual runs:
```bash
# Run all hooks on all files
make precommit

# Run specific hook
PRECOMMIT_ARGS="ruff --all-files" make precommit

# Update hooks to latest versions
make precommit-autoupdate
```

## Code formatting

The project uses `ruff` for Python code formatting and linting:

```bash
# Format code
make format

# Check linting issues (with fixes)
make check

# Lint without modifying files
make lint
```

## Testing

Run tests using pytest (via [uv](https://github.com/astral-sh/uv)) and disable
auto-loaded plugins that might rely on system paths:

```bash
# Run all tests
make test

# Run with coverage
make coverage

# Run specific test file or pattern
make test PYTEST_ARGS="tests/test_icons.py"
make test PYTEST_ARGS="-k icons -vv"

# After changing dependencies
make install
```

---

## License

[MIT](LICENSE)
