from fabric.hyprland.widgets import HyprlandWorkspaces, WorkspaceButton


class Workspace(HyprlandWorkspaces):
    def __init__(self):
        super().__init__(
            name="workspaces",
            buttons_factory=lambda ws_id: WorkspaceButton(id=ws_id, label=None)
        )

