import socket
import threading
from customtkinter import *


class ChatClient:
    def __init__(self):
        self.sock = None
        self.nickname = None
        self.host = None
        self.port = None
        self.running = False
        self.buffer = ""  # Буфер для неповних повідомлень

        # --- login window ---
        self.win = CTk()
        self.win.geometry("400x300")
        self.win.title("OP Overlord 🍋")

        CTkLabel(self.win, text="Nickname:", font=("Arial", 14, "bold")).pack(pady=5)
        self.nickname_entry = CTkEntry(self.win, placeholder_text="Anon")
        self.nickname_entry.pack(pady=5)

        CTkLabel(self.win, text="Host:", font=("Arial", 14, "bold")).pack(pady=5)
        self.host_entry = CTkEntry(self.win, placeholder_text="127.0.0.1")
        self.host_entry.pack(pady=5)

        CTkLabel(self.win, text="Port:", font=("Arial", 14, "bold")).pack(pady=5)
        self.port_entry = CTkEntry(self.win, placeholder_text="8081")
        self.port_entry.pack(pady=5)

        self.login_button = CTkButton(self.win, text="Login", command=self.connect_server)
        self.login_button.pack(pady=20)

        self.win.protocol("WM_DELETE_WINDOW", self.close_client)
        self.win.mainloop()

    def connect_server(self):
        self.host = self.host_entry.get().strip() or "127.0.0.1"
        self.nickname = self.nickname_entry.get().strip() or "Anon"
        port_text = self.port_entry.get().strip()
        try:
            self.port = int(port_text) if port_text else 8081
        except ValueError:
            self.show_error("Невірний порт")
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.sock.send(self.nickname.encode('utf-8'))
            print(f"✅ Підключено до {self.host}:{self.port}")
        except Exception as e:
            self.show_error(f"Помилка підключення: {e}")
            return

        self.running = True
        self.open_chat_window()

        self.win.after(100, lambda: threading.Thread(
            target=self.receive_messages, daemon=True
        ).start())

    def show_error(self, message):
        err = CTkToplevel(self.win)
        err.title("Помилка")
        err.geometry("300x100")
        CTkLabel(err, text=message, text_color="red").pack(pady=20)
        CTkButton(err, text="OK", command=err.destroy).pack()

    def open_chat_window(self):
        self.chat_root = self.win
        self.chat_root.title(f"Чат ({self.nickname}) 🍋")
        self.chat_root.geometry("700x500")

        for w in self.chat_root.winfo_children():
            w.destroy()

        main_frame = CTkFrame(self.chat_root)
        main_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.text_area = CTkTextbox(main_frame, wrap="word", state="disabled")
        self.text_area.pack(fill="both", expand=True, pady=5)

        entry_frame = CTkFrame(main_frame)
        entry_frame.pack(fill="x")

        self.entry = CTkEntry(entry_frame, placeholder_text="Введіть повідомлення...")
        self.entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        self.entry.bind("<Return>", lambda e: self.send_message())

        CTkButton(entry_frame, text="▶️", width=50, command=self.send_message).pack(side="right", padx=5)

        side_frame = CTkFrame(self.chat_root, width=150)
        side_frame.pack(side="right", fill="y", padx=10, pady=10)

        CTkLabel(side_frame, text="Користувачі", font=("Arial", 16)).pack(pady=10)
        self.user_list = CTkTextbox(side_frame, state="disabled", width=120)
        self.user_list.pack(fill="both", expand=True, padx=5, pady=5)

        self.chat_root.protocol("WM_DELETE_WINDOW", self.close_client)

    def receive_messages(self):
        print("🔄 Потік прийому запущено")
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                self.buffer += data.decode('utf-8')

                while True:
                    msg_idx = self.buffer.find("MSG:")
                    users_idx = self.buffer.find("USERS:")

                    if msg_idx == -1 and users_idx == -1:
                        break

                    if msg_idx != -1 and (users_idx == -1 or msg_idx < users_idx):
                        end_idx = self.buffer.find("MSG:", msg_idx + 4)
                        if end_idx == -1:
                            end_idx = self.buffer.find("USERS:", msg_idx + 4)
                        if end_idx == -1:
                            end_idx = len(self.buffer)
                        line = self.buffer[msg_idx:end_idx].strip()
                        self.buffer = self.buffer[end_idx:]
                        msg = line[4:].strip()
                        if msg:
                            self.chat_root.after_idle(lambda m=msg: self.add_message(m))

                    elif users_idx != -1:
                        end_idx = self.buffer.find("MSG:", users_idx + 6)
                        if end_idx == -1:
                            end_idx = self.buffer.find("USERS:", users_idx + 6)
                        if end_idx == -1:
                            end_idx = len(self.buffer)
                        line = self.buffer[users_idx:end_idx].strip()
                        self.buffer = self.buffer[end_idx:]
                        users_str = line[6:].strip()
                        users = [u.strip() for u in users_str.split(",") if u.strip()]
                        self.chat_root.after_idle(lambda u=users: self.update_user_list(u))
            except:
                break

        self.running = False
        try:
            self.sock.close()
        except:
            pass
        self.chat_root.after_idle(lambda: self.add_message("⚠️ З'єднання закрито."))

    def add_message(self, data: str):
        self.text_area.configure(state="normal")
        self.text_area.insert("end", data + "\n")
        self.text_area.see("end")
        self.text_area.configure(state="disabled")

    def update_user_list(self, users):
        self.user_list.configure(state="normal")
        self.user_list.delete("1.0", "end")
        for u in users:
            if "(" in u and ")" in u:
                name = u.split("(")[0].strip()
                lemons = u.split("(")[1].split(")")[0]
                self.user_list.insert("end", f"{name} 🍋 {lemons}\n")
            else:
                self.user_list.insert("end", f"{u}\n")
        self.user_list.configure(state="disabled")

    def send_message(self):
        msg = self.entry.get().strip()
        if msg:
            try:
                if msg.startswith("+lemon"):
                    self.sock.send(msg.encode('utf-8'))
                    self.add_message(f"🍋 Ви подарували лимон! ({msg})")
                else:
                    self.sock.send(msg.encode('utf-8'))
            except:
                self.add_message("⚠️ Втрачено зв'язок із сервером!")
                self.running = False
            self.entry.delete(0, "end")

    def close_client(self):
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except:
            pass
        self.win.destroy()


if __name__ == "__main__":
    ChatClient()
