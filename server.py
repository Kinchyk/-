import socket
import threading
from customtkinter import *
import queue

HOST = 'localhost'
PORT = 8081

clients = {}
lemons = {}
messages_sent = {}
lock = threading.Lock()

ui_queue = queue.Queue()


class ServerUI:
    def __init__(self):
        self.root = CTk()
        self.root.title("🍋 OP Overlord Server Panel")
        self.root.geometry("900x600")

        # --- LEFT: console ---
        console_frame = CTkFrame(self.root)
        console_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        CTkLabel(console_frame, text="Консоль сервера", font=("Arial", 16, "bold")).pack(pady=5)
        self.console = CTkTextbox(console_frame, wrap="word", state="disabled")
        self.console.pack(fill="both", expand=True, padx=5, pady=5)

        # --- RIGHT: user list ---
        user_frame = CTkFrame(self.root, width=250)
        user_frame.pack(side="right", fill="y", padx=10, pady=10)

        CTkLabel(user_frame, text="Користувачі 🍋", font=("Arial", 16, "bold")).pack(pady=5)
        self.user_container = CTkScrollableFrame(user_frame, width=230)
        self.user_container.pack(fill="both", expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Постійна перевірка черги
        self.root.after(100, self.process_ui_queue)

    def process_ui_queue(self):
        """Обробляє дії, надіслані з інших потоків"""
        try:
            while True:
                func = ui_queue.get_nowait()
                func()
        except queue.Empty:
            pass
        self.root.after(100, self.process_ui_queue)

    def log(self, message):
        """Додає рядок у консоль (через чергу, щоб не зависло)"""
        def do_log():
            self.console.configure(state="normal")
            self.console.insert("end", message + "\n")
            self.console.see("end")
            self.console.configure(state="disabled")

        ui_queue.put(do_log)

    def refresh_user_list(self):
        """Оновлення списку користувачів"""
        def do_refresh():
            for child in self.user_container.winfo_children():
                child.destroy()

            with lock:
                for nick, count in lemons.items():
                    frame = CTkFrame(self.user_container)
                    frame.pack(fill="x", pady=3)

                    CTkLabel(frame, text=f"{nick}: {count} 🍋", width=150, anchor="w").pack(side="left", padx=5)
                    CTkButton(frame, text="+", width=30,
                              command=lambda n=nick: self.safe_add_lemon(n)).pack(side="left", padx=2)
                    CTkButton(frame, text="-", width=30,
                              command=lambda n=nick: self.safe_remove_lemon(n)).pack(side="left", padx=2)
        ui_queue.put(do_refresh)

    def safe_add_lemon(self, nickname):
        threading.Thread(target=add_lemon_logic, args=(nickname,), daemon=True).start()

    def safe_remove_lemon(self, nickname):
        threading.Thread(target=remove_lemon_logic, args=(nickname,), daemon=True).start()

    def on_close(self):
        self.root.destroy()


ui = ServerUI()


def broadcast(message):
    with lock:
        for client in list(clients.keys()):
            try:
                client.send(message.encode('utf-8'))
            except:
                remove_client(client)


def broadcast_user_list():
    with lock:
        users = []
        for sock, nick in clients.items():
            count = lemons.get(nick, 0)
            users.append(f"{nick}({count})")
        users_str = ",".join(users)
    broadcast("USERS:" + users_str)
    ui.refresh_user_list()


def add_lemon_logic(nickname):
    with lock:
        if nickname in lemons:
            lemons[nickname] += 1
            broadcast(f"MSG:🍋 Сервер подарував лимон {nickname}!")
            broadcast_user_list()


def remove_lemon_logic(nickname):
    with lock:
        if nickname in lemons and lemons[nickname] > 0:
            lemons[nickname] -= 1
            broadcast_user_list()


def remove_client(sock):
    with lock:
        nickname = clients.pop(sock, None)
        if nickname:
            lemons.pop(nickname, None)
            messages_sent.pop(nickname, None)

    if nickname:
        ui.log(f"[Вийшов] {nickname}")
        broadcast(f"MSG:⚠️ {nickname} вийшов із чату")
        broadcast_user_list()


def handle_client(sock, addr):
    try:
        nickname = sock.recv(1024).decode('utf-8').strip()
        if not nickname:
            nickname = f"User{addr[1]}"

        with lock:
            clients[sock] = nickname
            lemons.setdefault(nickname, 0)
            lemons[nickname] += 1  # 🍋 1 лимон за підключення
            messages_sent[nickname] = 0

        ui.log(f"[Підключився] {nickname} з {addr}")
        broadcast(f"MSG:✅ {nickname} приєднався до чату (отримав 1 🍋)")
        broadcast_user_list()

        while True:
            data = sock.recv(4096)
            if not data:
                break

            message = data.decode('utf-8').strip()
            ui.log(f"[{nickname}] {message}")

            if message.startswith("+lemon"):
                parts = message.split()
                if len(parts) >= 2:
                    target = parts[1]
                    with lock:
                        if target in lemons and target != nickname:
                            lemons[target] += 1
                            broadcast(f"MSG:🍋 {nickname} подарував лимон {target}!")
                            broadcast_user_list()
                        else:
                            sock.send("MSG:⚠️ Невірний нік для +lemon".encode('utf-8'))
                else:
                    sock.send("MSG:⚠️ Використання: +lemon <нік>".encode('utf-8'))
            else:
                broadcast(f"MSG:{nickname}: {message}")

                # ✅ +1 лимон за кожні 10 повідомлень
                with lock:
                    messages_sent[nickname] += 1
                    if messages_sent[nickname] % 10 == 0:
                        lemons[nickname] += 1
                        broadcast(f"MSG:🍋 {nickname} отримав бонусний лимон за активність!")
                        broadcast_user_list()

    except Exception as e:
        ui.log(f"❌ Помилка клієнта: {e}")
    finally:
        remove_client(sock)
        sock.close()


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    ui.log(f"[Сервер запущено] {HOST}:{PORT}")

    def accept_clients():
        while True:
            sock, addr = server.accept()
            threading.Thread(target=handle_client, args=(sock, addr), daemon=True).start()

    threading.Thread(target=accept_clients, daemon=True).start()
    ui.root.mainloop()
    server.close()


if __name__ == "__main__":
    start_server()
