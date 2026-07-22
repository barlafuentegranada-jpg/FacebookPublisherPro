class Router:
    """Small page registry and route switcher for the UI shell."""

    def __init__(self, container, on_route_changed=None):
        self.container = container
        self.on_route_changed = on_route_changed
        self.pages = {}
        self.current_route = None

    def register(self, route, page):
        self.pages[route] = page
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_remove()

    def navigate(self, route):
        if route not in self.pages:
            raise KeyError(f"Unknown route: {route}")

        if self.current_route:
            self.pages[self.current_route].grid_remove()

        self.current_route = route
        self.pages[route].grid()

        if self.on_route_changed:
            self.on_route_changed(route, self.pages[route])

    def routes(self):
        return list(self.pages.keys())


NavigationManager = Router
