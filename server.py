import socket
import threading
import customtkinter as ctk

HOST = 'localhost'
PORT = 8081

clients = {}
lemons = {}
lock = threading.Lock()


def broadcast(message):
    with lock:
        for client in list(clients.keys()):
            try:
                client.send(message.encode('utf-8'))
            except:
                remove_client(client)


def handle_client(client):
    nickname = clients[client]
    try:
        while True:
            msg = client.recv(1024).decode('utf-8')
            if not msg:
                break
            broadcast(f"{nickname}: {msg}")
    except:
        pass
    finally:
        remove_client(client)


def remove_client(client):
    with lock:
        if client in clients:
            name = clients.pop(client)
            lemons.pop(name, None)
            update_clients()
            broadcast(f"{name} вийшов.")
            client.close()


def accept_clients(server_socket):
    while True:
        client, _ = server_socket.accept()
        client.send("Введи свій нік: ".encode('utf-8'))
        nickname = client.recv(1024).decode('utf-8')

        with lock:
            clients[client] = nickname
            lemons.setdefault(nickname, 0)

        update_clients()
        log(f"{nickname} підключився.")
        broadcast(f"{nickname} приєднався до чату.")

        threading.Thread(target=handle_client, args=(client,), daemon=True).start()


def start_server():
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((HOST, PORT))
        server.listen()
        log(f"Сервер запущено на {HOST}:{PORT}")
        threading.Thread(target=accept_clients, args=(server,), daemon=True).start()
    except Exception as e:
        log(f"Помилка запуску: {e}")


def add_lemon():
    selected = clients_box.get()
    if not selected:
        log("Не вибрано користувача.")
        return

    try:
        amount = int(lemon_entry.get())
    except ValueError:
        log("Введи число.")
        return

    with lock:
        lemons[selected] = lemons.get(selected, 0) + amount
    log(f"{selected} отримав {amount} лимонів.")
    update_clients()


def update_clients():
    clients_box.configure(values=list(lemons.keys()))
    users_text = "\n".join([f"{n}: {c}" for n, c in lemons.items()])
    users_label.configure(text=users_text or "Немає користувачів")


def log(text):
    log_box.configure(state="normal")
    log_box.insert("end", text + "\n")
    log_box.configure(state="disabled")
    log_box.see("end")


# === UI ===
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Lemon Server")
app.geometry("400x400")

start_btn = ctk.CTkButton(app, text="Запустити сервер", command=start_server)
start_btn.pack(pady=10)

clients_box = ctk.CTkComboBox(app, values=[])
clients_box.pack(pady=5)

lemon_entry = ctk.CTkEntry(app, placeholder_text="Кількість")
lemon_entry.pack(pady=5)

add_btn = ctk.CTkButton(app, text="Додати лимони", command=add_lemon)
add_btn.pack(pady=5)

users_label = ctk.CTkLabel(app, text="Немає користувачів", justify="left")
users_label.pack(pady=10)

log_box = ctk.CTkTextbox(app, width=360, height=150, state="disabled")
log_box.pack(pady=5)

app.mainloop()
