
from H5Gizmos import Stack, Button, LabelledInput, Text, Html, serve, schedule_task, Template

class ChatMember:

    def __init__(self, name, controller):
        self.name = name
        self.controller = controller
        self.make_dashboard()

    def make_dashboard(self):
        self.message_input = LabelledInput("message:", size=100).on_enter(self.add_message)
        self.send_button = Button("Send").set_on_click(self.add_message)
        self.message_stack = Stack([], title="Messages")
        self.status_text = Text("Making dashboard.")
        self.dashboard = (
            Template("""
            <div>
            <b class="MESSAGE"/> <b class="ADD_BUTTON"/>
            <h1> Chat messages for chatter %s </h1>
            <div class="MESSAGE_LIST"/>
            </div>
            """ % self.name)
            .put(self.message_input.label_container, "MESSAGE")
            .put(self.send_button, "ADD_BUTTON")
            .put(self.message_stack, "MESSAGE_LIST")
        )
        self.dashboard.css_file("./simple_todo.css")
        self.dashboard.addClass("simple-todo")

    def info(self, message):
        self.status_text.html(message)

    def add_message(self, *ignored):
        message = self.message_input.value.strip()
        if not message:
            return self.info("Please provide a message.")
        self.info("posting message: " + message)
        self.controller.post_message("<div><b> %s : </b> <em> %s </em>" % (self.name, message))
        self.message_input.set_value("")

    def update_messages(self, messages):
        children = [Html(message) for message in messages]
        self.info("Updating messages: " + repr(len(messages)))
        self.message_stack.attach_children(children)

    async def startup(self):
        started = await self.dashboard.has_started()
        assert started, self.name + " failed to start."
        self.dashboard.on_shutdown(self.leave)
        self.controller.post_message("<em> %s joins </em>" % self.name)
        self.controller.update_all_chatters()

    def leave(self, *ignored):
        import sys
        self.controller.chatters.remove(self)
        self.controller.post_message("<em> %s leaves </em>" % self.name)
        if len(self.controller.chatters) < 1:
            sys.exit()

class ChatController:

    def __init__(self, nmembers=2):
        self.chatters = [ChatMember("person"+str(i), self) for i in range(nmembers)]
        self.message_list = []

    def post_message(self, message):
        self.message_list.append(message)
        self.update_all_chatters()

    def update_all_chatters(self):
        messages = self.message_list
        if len(messages) == 0:
            messages = ["<em> No messages </em>"]
        for chatter in self.chatters:
            chatter.update_messages(messages)

    async def start_chatters(self):
        print("Starting chatters, please use CONTROL-C to exit.")
        for chatter in self.chatters:
            await chatter.dashboard.link(
                verbose=False, 
                await_start=False,
                shutdown_on_close=False,
                )
            print()
            print("chatter", chatter.name, "available at", chatter.dashboard.entry_url())
            print()
            schedule_task(chatter.startup())

if __name__ == "__main__":
    Chatters = ChatController()
    serve(Chatters.start_chatters())
