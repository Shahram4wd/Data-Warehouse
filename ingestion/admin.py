from django.contrib import admin
from .models import (
    Genius_DivisionGroup,  # Updated import
    Genius_Division,  # Updated import
    Genius_UserData,  # Updated import
    Genius_Prospect,  # Updated import
    Genius_Appointment,  # Updated import
    Genius_Quote,  # Updated import
    Genius_MarketingSource,  # Updated import
)

# Register models with the admin site
admin.site.register(Genius_DivisionGroup)
admin.site.register(Genius_Division)
admin.site.register(Genius_UserData)
admin.site.register(Genius_Prospect)
admin.site.register(Genius_Appointment)
admin.site.register(Genius_Quote)
admin.site.register(Genius_MarketingSource)
