# taskbird/forms.py
from django import forms
from taskbird.models import Ticket, Category, Priority, TicketAttachment

class TicketForm(forms.ModelForm):
    attachments = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'block w-full text-sm text-gray-700 border border-gray-300 rounded-lg shadow-sm file:bg-blue-50 file:border-0 file:px-4 file:py-2 file:rounded-full file:text-blue-700 hover:file:bg-blue-100'
        }),
        required=False,
        help_text="Upload a relevant file (max 5MB, JPEG/PNG/PDF)."
    )

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'category', 'priority']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter ticket title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 5,
                'placeholder': 'Describe your issue'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'priority': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default priority (e.g., Low or ID=1)
        try:
            self.fields['priority'].initial = Priority.objects.get(id=1)
        except Priority.DoesNotExist:
            pass
        # Make category optional
        self.fields['category'].required = False

    def clean_attachments(self):
        file = self.cleaned_data.get('attachments')
        if file:
            max_size = 5 * 1024 * 1024  # 5MB
            allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
            if file.size > max_size:
                raise forms.ValidationError(f"File {file.name} exceeds 5MB limit.")
            if file.content_type not in allowed_types:
                raise forms.ValidationError(f"File {file.name} is not a supported type (JPEG, PNG, PDF).")
        return file