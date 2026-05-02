import flet as ft

def main(page: ft.Page):
    page.title = "Mi App Multiplataforma"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    # Función que se ejecuta al hacer clic
    def saludar(e):
        if not nombre.value:
            nombre.error_text = "Por favor, escribe algo"
            page.update()
        else:
            page.add(ft.Text(f"¡Hola {nombre.value}!, bienvenido a tu app."))
            nombre.value = ""
            page.update()

    # Componentes de la interfaz
    nombre = ft.TextField(label="¿Cómo te llamas?", width=300)
    
    page.add(
        ft.Text("Bienvenido", size=30, weight=ft.FontWeight.BOLD),
        ft.Card(
            content=ft.Container(
                content=ft.Column([
                    nombre,
                    ft.ElevatedButton("Enviar datos", on_click=saludar),
                ]),
                padding=20
            )
        )
    )

# ft.app(target=main) # Para ejecutar como ventana de escritorio
ft.app(target=main)