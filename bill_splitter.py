import json
from decimal import Decimal, InvalidOperation

from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Header, Footer, Input, Static, Label, SelectionList
from textual.widgets.selection_list import Selection
from textual.message import Message
from textual.widget import Widget

# --- NEW WIDGET FOR PERSON INPUT ---
class PersonInput(Widget):
    """A widget containing a person's name, input, and a remove button."""

    # Define a custom message that this widget can send
    class Remove(Message):
        """Message posted when the remove button is clicked."""
        # Add an __init__ to hold a direct reference to the widget to remove.
        def __init__(self, to_remove: Widget) -> None:
            self.to_remove = to_remove
            super().__init__()

    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.person_name = name
        self.input = Input(placeholder="0.00")

    def compose(self) -> ComposeResult:
        """Create the child widgets."""
        with Horizontal():
            yield self.input
            yield Button("✕", variant="error", classes="remove-button")

    def on_mount(self) -> None:
        """Set the border title when the widget is mounted."""
        # We set the border title here to display the person's name
        self.border_title = self.person_name

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Post the Remove message when the button is clicked."""
        self.post_message(self.Remove(self))

    @property
    def value(self) -> str:
        """The value of the input field."""
        return self.query_one(Input).value

    def focus_input(self) -> None:
        """Give focus to the internal Input widget."""
        self.input.focus()


# --- MODAL SCREEN (Unchanged from previous version) ---
class SelectPersonScreen(ModalScreen[list[str]]):
    """A modal screen to select one or more people from a list."""
    def __init__(self, people: list[str]) -> None:
        self.people = people
        super().__init__()
    def compose(self) -> ComposeResult:
        with Vertical(id="select_person_dialog"):
            yield Label("Select people to add (use Spacebar):")
            yield SelectionList[str](
                *[Selection(person, person, id=person) for person in self.people]
            )
            with Vertical(id="dialog_buttons"):
                yield Button("Add Selected", variant="primary", id="add")
                yield Button("Cancel", id="cancel")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add":
            self.dismiss(self.query_one(SelectionList).selected)
        elif event.button.id == "cancel":
            self.dismiss([])

# --- MAIN APP (Updated to use the new PersonInput widget) ---
class BillSplitterApp(App):
    """A Textual app to split a bill among a variable number of people."""
    CSS_PATH = "bill_splitter.css"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"), ("escape", "dismiss_modal", "Dismiss Modal")]

    def __init__(self):
        self.all_people = []
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Enter amounts for each person:"),
            VerticalScroll(id="people_list"),
            Button("Add Person", id="add_person"),
            Input(placeholder="Other charges (e.g., 15/2)", id="other_charges"),
            Button("Calculate", variant="primary", id="calculate"),
            Static(id="results"),
            id="main_container"
        )
        yield Footer()

    def on_mount(self) -> None:
        try:
            with open("people.json", "r") as f:
                self.all_people = json.load(f)
        except FileNotFoundError:
            self.query_one("#results").update("[bold red]Error: people.json not found.[/bold red]")
        except json.JSONDecodeError:
            self.query_one("#results").update("[bold red]Error: Could not decode people.json.[/bold red]")

    def _safe_eval(self, expression: str) -> Decimal:
        if not expression: return Decimal(0)
        try:
            return Decimal(eval(expression, {"__builtins__": None}, {}))
        except Exception:
            return Decimal(0)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "calculate":
            self.calculate_split()
        elif event.button.id == "add_person":
            self.action_add_person()

    def action_add_person(self) -> None:
        """Show a modal to add new people."""
        current_people = {inp.border_title for inp in self.query(PersonInput)}
        available_people = [p for p in self.all_people if p not in current_people]

        if not available_people:
            self.query_one("#results").update("[bold yellow]All people from people.json have been added.[/bold yellow]")
            return

        def add_people_callback(people_names: list[str]) -> None:
            if people_names:
                people_list = self.query_one("#people_list")
                last_input = None
                for name in people_names:
                    person_widget = PersonInput(name=name)
                    people_list.mount(person_widget)
                    last_input = person_widget
                if last_input:
                    last_input.focus_input()

        self.push_screen(SelectPersonScreen(available_people), add_people_callback)

    # --- NEW: Handler for the custom Remove message ---
    def on_person_input_remove(self, message: PersonInput.Remove) -> None:
        """Called when a remove button is clicked on a PersonInput."""
        # message.control is the widget that sent the message
        message.to_remove.remove()
        self.query_one("#results").update("Person removed.")

    def calculate_split(self) -> None:
        """Perform the bill splitting calculation."""
        results_widget = self.query_one("#results")
        try:
            person_widgets = self.query(PersonInput)
            L = [self._safe_eval(widget.value) for widget in person_widgets]
            
            other_charges_input = self.query_one("#other_charges", Input)
            other_charges = self._safe_eval(other_charges_input.value)

            total = sum(L)
            if total == 0:
                if other_charges > 0 and person_widgets:
                    num_people = len(person_widgets)
                    split_other_charges = other_charges / num_people
                    output = (f"[bold]Total: {other_charges:.2f}[/bold]\n\n"
                              f"[bold]Final amounts (charges split equally):[/bold]\n")
                    for widget in person_widgets:
                        output += f"{widget.border_title}: {split_other_charges:.2f}\n"
                    results_widget.update(output)
                else:
                    results_widget.update("Nothing to calculate.")
                return

            weights = [x / total for x in L]
            output = (f"[bold]Subtotal: {total:.2f}\n"
                      f"Grand Total: {total + other_charges:.2f}[/bold]\n\n"
                      f"[bold]Final amounts per person:[/bold]\n")
            for i, (l, w) in enumerate(zip(L, weights)):
                final_amount = l + other_charges * w
                name = person_widgets[i].border_title
                output += f"{name}: {final_amount:.2f}\n"
            results_widget.update(output)

        except InvalidOperation:
            results_widget.update("[bold red]Error: Invalid number or expression.[/bold red]")

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark
    
    def action_dismiss_modal(self) -> None:
        if isinstance(self.screen, ModalScreen):
            self.pop_screen()

if __name__ == "__main__":
    app = BillSplitterApp()
    app.run()