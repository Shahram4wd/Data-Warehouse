from ingestion.models import Arrivy_Group

print(f'Total groups: {Arrivy_Group.objects.count()}')
print('Sample groups:')
for group in Arrivy_Group.objects.all()[:5]:
    print(f'  {group.id}: {group.name} - {group.city}, {group.state}')
