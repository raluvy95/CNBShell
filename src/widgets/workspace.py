from typing import Callable, Iterable

from fabric.hyprland.widgets import WorkspaceButton, get_hyprland_connection
from fabric.core.widgets import Workspaces
from fabric.hyprland.service import HyprlandEvent
from fabric.utils.helpers import bulk_connect
from fabric.utils import logger
import json

class HyprlandWorkspaces(Workspaces):
    def __init__(
        self,
        buttons: Iterable[WorkspaceButton] | None = None,
        buttons_factory: Callable[[int], WorkspaceButton | None]
        | None = lambda ws_id: WorkspaceButton(id=ws_id, label=None),
        invert_scroll: bool = False,
        empty_scroll: bool = False,
        **kwargs,
    ):
        super().__init__(buttons, buttons_factory, invert_scroll, **kwargs)
        self.connection = get_hyprland_connection()

        self._empty_scroll = empty_scroll
        bulk_connect(
            self.connection,
            {
                "event::workspacev2": self.on_workspace,
                "event::focusedmonv2": self.on_monitor,
                "event::createworkspacev2": self.on_create_workspace,
                "event::destroyworkspacev2": self.on_destroy_workspace,
                "event::urgent": self.on_urgent,
            },
        )

        # all aboard...
        if self.connection.ready:
            self.on_ready()
        else:
            self.connection.connect("notify::ready", self.on_ready)
        self.connect("scroll-event", self.do_handle_scroll)

    def on_ready(self):
        open_workspaces: tuple[int, ...] = tuple(
            workspace["id"]
            for workspace in json.loads(
                self.connection.send_command("j/workspaces").reply.decode()
            )
        )
        active_workspace = json.loads(
            self.connection.send_command("j/activeworkspace").reply.decode()
        )["id"]

        for id in open_workspaces:
            self.workspace_created(id)
            if id == active_workspace:
                self.workspace_activated(id)
        return

    def on_monitor(self, _, event: HyprlandEvent):
        if len(event.data) != 2:
            return
        return self.workspace_activated(int(event.data[1]))

    def on_workspace(self, _, event: HyprlandEvent):
        if len(event.data) != 2:
            return
        return self.workspace_activated(int(event.data[0]))

    def on_create_workspace(self, _, event: HyprlandEvent):
        if len(event.data) != 2:
            return
        return self.workspace_created(int(event.data[0]))

    def on_destroy_workspace(self, _, event: HyprlandEvent):
        if len(event.data) != 2:
            return
        return self.workspace_destroyed(int(event.data[0]))

    def on_urgent(self, _, event: HyprlandEvent):
        if len(event.data) != 1:
            return

        clients = json.loads(self.connection.send_command("j/clients").reply.decode())
        clients_map = {client["address"]: client for client in clients}
        urgent_client: dict = clients_map.get("0x" + event.data[0], {})
        if not (raw_workspace := urgent_client.get("workspace")):
            return logger.warning(
                f"[Workspaces] received urgent signal, but data received ({event.data[0]}) is incorrect, skipping..."
            )
        return self.urgent(int(raw_workspace["id"]))

    # fixes for hyprland 0.55
    def do_action_next(self):
        ws_arg = "e+1" if not self._empty_scroll else "+1"
        return self.connection.send_command(
            f"eval hl.dispatch(hl.dsp.focus({{ workspace = '{ws_arg}' }}))"
        )

    def do_action_previous(self):
        ws_arg = "e-1" if not self._empty_scroll else "-1"
        return self.connection.send_command(
            f"eval hl.dispatch(hl.dsp.focus({{ workspace = '{ws_arg}' }}))"
        )

    def do_button_clicked(self, button: WorkspaceButton):
        return self.connection.send_command(
            f"eval hl.dispatch(hl.dsp.focus({{ workspace = '{button.id}' }}))"
        )


class Workspace(HyprlandWorkspaces):
    def __init__(self):
        super().__init__(
            name="workspaces",
            buttons_factory=lambda ws_id: WorkspaceButton(id=ws_id, label=None)
        )

