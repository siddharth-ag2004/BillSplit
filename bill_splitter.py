import json
from decimal import Decimal, InvalidOperation

from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Header, Footer, Input, Static, Label, SelectionList
from textual.widgets.selection_list import Selection

# --- THIS MODAL SCREEN IS UPDATED ---
class SelectPersonScreen(ModalScreen[list[str]]):
    """A modal screen to select one or more people from a list."""

    def __init__(self, people: list[str]) -> None:
        self.people = people
        super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical(id="select_person_dialog"):
            # Updated the label to be more instructive
            yield Label("Select people to add (use Spacebar):")
            yield SelectionList[str](
                *[Selection(person, person, id=person) for person in self.people]
            )
            with Horizontal(id="dialog_buttons"):
                yield Button("Add Selected", variant="primary", id="add")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add":
            selection_list = self.query_one(SelectionList)
            # Dismiss with the entire list of selected people
            self.dismiss(selection_list.selected)
        elif event.button.id == "cancel":
            # Dismiss with an empty list on cancel
            self.dismiss([])

# --- THE MAIN APP IS UPDATED TO HANDLE MULTIPLE PEOPLE ---
class BillSplitterApp(App):
    """A Textual app to split a bill among a variable number of people."""

    CSS_PATH = "bill_splitter.css"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"), ("escape", "dismiss_modal", "Dismiss Modal")]

    def __init__(self):
        self.all_people = []
        super().__init__()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Vertical(
            # Label("Enter amounts or expressions for each person:"),
            VerticalScroll(id="people_list"),
            Button("Add Person", id="add_person"),
            Input(placeholder="Other charges (e.g., 15/2)", id="other_charges"),
            Button("Calculate", variant="primary", id="calculate"),
            Static(id="results"),
            id="main_container"
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is first mounted."""
        try:
            with open("people.json", "r") as f:
                self.all_people = json.load(f)
        except FileNotFoundError:
            self.query_one("#results").update("[bold red]Error: people.json not found.[/bold red]")
        except json.JSONDecodeError:
            self.query_one("#results").update("[bold red]Error: Could not decode people.json.[/bold red]")

    def _safe_eval(self, expression: str) -> Decimal:
        """Safely evaluate a mathematical expression."""
        if not expression:
            return Decimal(0)
        try:
            result = eval(expression, {"__builtins__": None}, {})
            return Decimal(result)
        except Exception:
            return Decimal(0)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "calculate":
            self.calculate_split()
        elif event.button.id == "add_person":
            self.action_add_person()

    def action_add_person(self) -> None:
        """Show a modal to add new people."""
        current_people = {inp.border_title for inp in self.query_one("#people_list").query(Input)}
        available_people = [p for p in self.all_people if p not in current_people]

        if not available_people:
            self.query_one("#results").update("[bold yellow]All people from people.json have been added.[/bold yellow]")
            return

        # --- THIS CALLBACK IS UPDATED ---
        def add_people_callback(people_names: list[str]) -> None:
            """Callback to add inputs for all selected people."""
            if people_names:
                people_list = self.query_one("#people_list")
                last_input = None
                for name in people_names:
                    person_input = Input()
                    person_input.border_title = name
                    people_list.mount(person_input)
                    last_input = person_input
                # Focus the last input that was added
                if last_input:
                    last_input.focus()

        self.push_screen(SelectPersonScreen(available_people), add_people_callback)


    def calculate_split(self) -> None:
        """Perform the bill splitting calculation and display the results."""
        results_widget = self.query_one("#results")
        try:
            person_inputs = self.query_one("#people_list").query(Input)
            L = [self._safe_eval(i.value) for i in person_inputs]

            other_charges_input = self.query_one("#other_charges", Input)
            other_charges = self._safe_eval(other_charges_input.value)

            total = sum(L)

            if total == 0:
                if other_charges > 0 and person_inputs:
                    num_people = len(person_inputs)
                    split_other_charges = other_charges / num_people
                    output = f"[bold]Total before other charges: 0.00\n"
                    output += f"Grand Total: {other_charges:.2f}[/bold]\n\n"
                    output += "[bold]Final amounts per person (charges split equally):[/bold]\n"
                    for person_input in person_inputs:
                        name = person_input.border_title
                        output += f"{name}: {split_other_charges:.2f}\n"
                    results_widget.update(output)
                else:
                    results_widget.update("Nothing to calculate.")
                return

            weights = [x / total for x in L]

            output = f"[bold]Total before other charges: {total:.2f}\n"
            output += f"Grand Total: {total + other_charges:.2f}[/bold]\n\n"
            output += "[bold]Final amounts per person:[/bold]\n"

            for i, (l, w) in enumerate(zip(L, weights)):
                final_amount = l + other_charges * w
                name = person_inputs[i].border_title
                output += f"{name}: {final_amount:.2f}\n"

            results_widget.update(output)

        except InvalidOperation:
            results_widget.update("[bold red]Error: Please enter valid numbers or expressions.[/bold red]")

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark
    
    def action_dismiss_modal(self) -> None:
        """Action to dismiss the top-most screen (our modal)."""
        if isinstance(self.screen, ModalScreen):
            self.pop_screen()


if __name__ == "__main__":
    app = BillSplitterApp()
    app.run()