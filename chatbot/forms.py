from django import forms


class ChatMessageForm(forms.Form):
    message = forms.CharField(
        label="Sua mensagem",
        max_length=1000,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Digite sua pergunta para a IA...",
                "class": "chat-input",
            }
        ),
    )
