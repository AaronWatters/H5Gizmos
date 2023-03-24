"""
A quick and dirty multi-person chat interface using H5Gizmos.
"""

import time

import H5Gizmos as gz

from H5Gizmos.python.gizmo_launch_url import add_launcher
from H5Gizmos.python.examine import explorer

class ChatController:

    """
    Central hub for launching new chat member interfaces and communicating messages.
    """

    def __init__(self):
        self.members = []
        self.messages = []

    def add_message(self, message):
        self.messages.append(message)
        fmt = self.format_messages()
        for member in self.members:
            member.display_messages(fmt)

    def format_messages(self):
        msgs = self.messages
        if len(msgs)<1:
            return "<div><b>No messages</b></div>"
        else:
            msg_list = [x.format() for x in msgs]
            return "<div>%s</div>" % ("\n".join(msg_list),)
        
    def make_gizmo(self):
        self.full_path = gz.Text("Not initialized.")
        self.launch_link = gz.Html("<div>Not initialized.</div>")
        self.dashboard = (
            gz.Template("""
                <div>
                    <p class="FULL_PATH"/>
                    <p class="LAUNCH_LINK"/>
                </div>
            """)
            .put(self.full_path, "FULL_PATH")
            .put(self.launch_link, "LAUNCH_LINK")
        )
        return self.dashboard
    
    async def startup(self):
        dashboard = self.make_gizmo()
        #started = await dashboard.has_started()
        await dashboard.link()
        #assert started, "ChatController failed to start."
        parent = dashboard
        #parent = None
        (relative, full, path) = add_launcher(
            dashboard.gizmo, self.add_new_member, parent_component=parent)
        self.full_path.text(full)
        self.launch_link.html(
            '<a href="%s">%s</a>' % (relative, relative)
        )
        # debug explorer
        exp = explorer(self)
        dashboard.add(exp.gizmo())
    
    def add_new_member(self):
        print("add new member called.")
        #component = gz.Text("TEMP FOR DEBUGGING.")
        member = ChatMember(self)
        self.members.append(member)
        component = member.dashboard
        return component

class ChatMember:

    """
    Model for an individual chat participant.
    """

    def __init__(self, controller):
        self.controller = controller
        self.nickname = None
        self.instructions = gz.Html("<div>Please provide a nickname for chat.</div>")
        self.prompt = gz.Html("<b><em>Nickname:</em></b>")
        self.input = gz.Input(size=100)
        self.input.on_enter(self.send)
        self.send_button = gz.Button("Send").set_on_click(self.send)
        fmt = controller.format_messages()
        self.messages = gz.Html(fmt)
        self.status_text = gz.Html("<em>Please provide a nickname to log in.</em>")
        self.dashboard = gz.Stack([
            self.instructions,
            [self.prompt, self.input, self.send_button],
            self.messages,
            self.status_text,
        ])

    def send(self, *ignored):
        msg = self.input.value.strip()
        ln = len(msg)
        if self.nickname is None:
            if ln < 1:
                self.info("Please provide non-empty nickname to log in.")
            else:
                self.nickname = msg
                self.instructions.html("Enter a message to send.")
                self.prompt.html("<em>Message</em>")
                self.info("logging in as " + repr(self.nickname))
                message = ChatMessage("", repr(self.nickname) + " logged in.")
                self.controller.add_message(message)
                title = repr(self.nickname) + " chatting"
                # window.document.title = title
                gz.do(self.dashboard.window.document._set("title", title))
        else:
            if ln < 1:
                self.info("Please send a non-empty message.")
            else:
                self.info("Sending: " + repr(ln))
                message = ChatMessage(self.nickname, msg)
                self.controller.add_message(message)
        self.input.set_value("")

    def display_messages(self, fmt):
        self.messages.html(fmt)

    def info(self, message):
        self.status_text.html(message)

class ChatMessage:

    """
    Container for a chat message.
    """

    def __init__(self, sender, text):
        self.sender = sender
        self.text = text
        self.time = time.ctime()

    def format(self):
        return "<div><em>%s %s: </em> %s </div>" % (self.time, self.sender, self.text)
    
def create_chat_server():
    controller = ChatController()
    gz.serve(controller.startup())

if __name__ == "__main__":
    create_chat_server()
