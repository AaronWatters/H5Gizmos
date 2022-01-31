
"""
A todo list user interface.
"""

from H5Gizmos import Stack, Button, LabelledInput, Text, Html, serve, ClickableText, Template
import json, os

class TodoList:

    def __init__(self, file="./todos.json"):
        self.entries = []
        self.file = file
        if os.path.exists(file):
            with open(file) as f:
                json_entries = json.load(f)
            self.entries = [todo_from_json_object(ob, self) for ob in json_entries]
        self.make_dashboard()

    def make_dashboard(self):
        self.new_item_input = LabelledInput("add item:", size=100).on_enter(self.add_item)
        self.add_button = Button("Add to do").set_on_click(self.add_item)
        self.pending_stack = Stack([], title="Pending items")
        self.done_stack = Stack([], title="Done items")
        self.status_text = Text("Making dashboard.")
        self.dashboard = (
            Template("""
            <table>
                    <tr> <td colspan="2"> <h1>To do list</h1> </td> </tr>
                    <tr> <td colspan="2">
                        <em class="ADD_INPUT"/> <em class="ADD_BUTTON"/>
                    </td></tr>
                    <tr>
                        <td>
                            <h3>Pending items</h3>
                            <div class="PENDING"/>
                        </td>
                        <td>
                            <h3>Done!</h3>
                            <div class="DONE"/>
                        </td>
                    </tr>
                    <tr> <td colspan="2" class="STATUS"/> </tr>
            </table>
            """)
            .put(self.new_item_input.label_container, "ADD_INPUT")
            .put(self.add_button, "ADD_BUTTON")
            .put(self.pending_stack, "PENDING")
            .put(self.done_stack, "DONE")
            .put(self.status_text, "STATUS")
        )
        self.dashboard.css_file("./simple_todo.css")
        self.dashboard.addClass("simple-todo")

    def info(self, message):
        self.status_text.html(message)

    def update_dashboard(self):
        entries = self.entries = [e for e in self.entries if e.status != "deleted"]
        pending = []
        done = []
        for entry in entries:
            if entry.status == "pending":
                pending.append(entry.display())
            else:
                done.append(entry.display())
        for (stack, sequence) in [(self.pending_stack, pending), (self.done_stack, done)]:
            if sequence:
                stack.attach_children(sequence)
            else:
                stack.attach_children(["<em>No entries</em>"])
        with open(self.file, "w") as f:
            json.dump([todo.to_json_object() for todo in self.entries], f)
        self.info("Updated to do list with %s entries." % len(entries))

    def add_item(self, *ignored):
        description = self.new_item_input.value
        if not description:
            return self.info("Please provide a description.")
        self.entries.append(Todo(description, in_list=self))
        self.update_dashboard()
        self.new_item_input.set_value("")

class Todo:

    colors = dict(pending="orange", done="blue", deleted="red")

    def __init__(self, description, status="pending", in_list=None):
        self.description = description
        self.status = status
        self.in_list = in_list

    def display(self):
        return ClickableText(self.description, on_click=self.on_click, color=self.colors[self.status])

    def on_click(self, *ignored):
        next_status = dict(pending="done", done="deleted", deleted="deleted")
        self.status = next_status[self.status]
        if self.in_list:
            self.in_list.update_dashboard()

    def to_json_object(self):
        return dict(status=self.status, description=self.description)

def todo_from_json_object(ob, in_list=None):
    return Todo(ob["description"], ob["status"], in_list)

async def task():
    todos = TodoList()
    await todos.dashboard.browse()
    await todos.dashboard.validate_classes()
    todos.update_dashboard()
    todos.new_item_input.focus()

if __name__ == "__main__":
    serve(task())
