# set the history file size
export HISTFILESIZE=3000

export PATH=/usr/local/bin:$PATH

if [ -f "/usr/local/bin/virtualenvwrapper.sh" ] ; then
    export WORKON_HOME=~/.venvs
    source /usr/local/bin/virtualenvwrapper.sh
fi

# add local bin directory to path for tools
if [ -d "$HOME/bin" ] ; then
    PATH="$HOME/bin:$PATH"
fi

# add local python bins to path (pip install --user)
if [ -d "$HOME/.local/bin" ] ; then
    PATH="$HOME/.local/bin:$PATH"
fi

if [ -f "$HOME/.bash_aliases" ]; then
    . "$HOME/.bash_aliases"
fi

PROMPT_COMMAND="PS1=\$(python ~/bin/git_status.py)"

export EDITOR=vim

export PATH
