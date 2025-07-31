
"""
People Management CLI Application
Manages people, contact details, and group memberships using SQLAlchemy ORM.
"""

import argparse
import json
import csv
import sys
from datetime import datetime
from typing import List, Dict

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.exc import SQLAlchemyError

Base = declarative_base()

# Association table for many-to-many relationship between Person and Group
person_group = Table(
    'person_group',
    Base.metadata,
    Column('person_id', Integer, ForeignKey('person.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('group.id'), primary_key=True)
)


class Person(Base):
    """Implementation of class Person"""
    __tablename__ = 'person'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)

    # One-to-One relationship with ContactInfo
    contact_info = relationship("ContactInfo", back_populates="person",
                                uselist=False, cascade="all, delete-orphan")

    # Many-to-Many relationship with Group
    groups = relationship("Group", secondary=person_group,
                          back_populates="people")


class ContactInfo(Base):
    """Implementation of class ContactInfo"""
    __tablename__ = 'contact_info'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    person_id = Column(Integer, ForeignKey('person.id'),
                       nullable=False, unique=True)

    # One-to-One relationship with Person
    person = relationship("Person", back_populates="contact_info")


class Group(Base):
    """Implementation of class Group"""
    __tablename__ = 'group'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)

    # Many-to-Many relationship with Person
    people = relationship("Person", secondary=person_group,
                          back_populates="groups")


class ChangeLog(Base):
    """Implementation of class ChangeLog"""
    __tablename__ = 'change_log'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    entity = Column(String(50), nullable=False)
    action = Column(String(20), nullable=False)
    details = Column(String(500), nullable=False)


class DatabaseManager:
    """Implementation of main class DatabaseManager"""
    def __init__(self, db_url: str = "sqlite:///people.db"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def _log_change(self, session: Session, entity: str, action: str, details: str):
        """Log changes to the ChangeLog table"""
        log_entry = ChangeLog(entity=entity, action=action, details=details)
        session.add(log_entry)

    def _validate_name(self, name: str) -> bool:
        """Validate name is not empty and <= 100 characters"""
        return bool(name and name.strip() and len(name.strip()) <= 100)

    def _validate_age(self, age: int) -> bool:
        """Validate age > 0"""
        return age > 0

    def _validate_email(self, email: str) -> bool:
        """Validate email contains @"""
        return '@' in email

    def _validate_phone(self, phone: str) -> bool:
        """Validate phone is digits only"""
        return phone.isdigit() if phone else True

    def create_person(self, name: str, age: int) -> int:
        """Create a new person and return their ID"""
        if not self._validate_name(name):
            raise ValueError("Name must not be empty and <= 100 characters")
        if not self._validate_age(age):
            raise ValueError("Age must be > 0")

        session = self.Session()
        try:
            person = Person(name=name.strip(), age=age)
            session.add(person)
            session.commit()

            self._log_change(session, "Person", "create", f"Created person: {name}, age: {age}")
            session.commit()

            return person.id
        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Database error: {str(e)}") from e
        finally:
            session.close()

    def add_or_update_contact(self, person_id: int, email: str, phone: str = None) -> bool:
        """Add or update contact info for a person"""
        if not self._validate_email(email):
            raise ValueError("Invalid email format")
        if phone and not self._validate_phone(phone):
            raise ValueError("Phone must contain only digits")

        session = self.Session()
        try:
            person = session.query(Person).filter_by(id=person_id).first()
            if not person:
                raise ValueError(f"Person with ID {person_id} not found")

            if person.contact_info:
                # Update existing contact info
                person.contact_info.email = email
                person.contact_info.phone = phone
                action = "update"
            else:
                # Create new contact info
                contact_info = ContactInfo(email=email, phone=phone, person_id=person_id)
                session.add(contact_info)
                action = "create"

            session.commit()

            self._log_change(session, "ContactInfo", action,
                             f"Contact info for person {person_id}: {email}, {phone}")
            session.commit()

            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Database error: {str(e)}") from e
        finally:
            session.close()

    def create_group(self, name: str) -> int:
        """Create a new group and return its ID"""
        if not self._validate_name(name):
            raise ValueError("Group name must not be empty and <= 100 characters")

        session = self.Session()
        try:
            group = Group(name=name.strip())
            session.add(group)
            session.commit()

            self._log_change(session, "Group", "create", f"Created group: {name}")
            session.commit()

            return group.id
        except SQLAlchemyError as e:
            session.rollback()
            if "UNIQUE constraint failed" in str(e):
                raise ValueError(f"Group '{name}' already exists")
            raise RuntimeError(f"Database error: {str(e)}")
        finally:
            session.close()

    def assign_group(self, person_id: int, group_id: int) -> bool:
        """Assign a person to a group"""
        session = self.Session()
        try:
            person = session.query(Person).filter_by(id=person_id).first()
            if not person:
                raise ValueError(f"Person with ID {person_id} not found")

            group = session.query(Group).filter_by(id=group_id).first()
            if not group:
                raise ValueError(f"Group with ID {group_id} not found")

            # Check if already assigned
            if group not in person.groups:
                person.groups.append(group)
                session.commit()

                self._log_change(session, "PersonGroup", "create",
                                 f"Assigned person {person_id} to group {group_id}")
                session.commit()

            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Database error: {str(e)}") from e
        finally:
            session.close()

    def read_people(self, filters: dict) -> List[Dict]:
        """Read people with optional filters"""
        session = self.Session()
        try:
            query = session.query(Person)

            # Apply filters
            if filters.get('min_age'):
                query = query.filter(Person.age >= filters['min_age'])
            if filters.get('max_age'):
                query = query.filter(Person.age <= filters['max_age'])
            if filters.get('name_contains'):
                query = query.filter(Person.name.contains(filters['name_contains']))
            if filters.get('group'):
                query = query.join(Person.groups).filter(Group.name == filters['group'])

            # Apply sorting
            if filters.get('sort_by'):
                if filters['sort_by'] == 'name':
                    query = query.order_by(Person.name)
                elif filters['sort_by'] == 'age':
                    query = query.order_by(Person.age)
                elif filters['sort_by'] == 'id':
                    query = query.order_by(Person.id)

            # Apply pagination
            if filters.get('offset'):
                query = query.offset(filters['offset'])
            if filters.get('limit'):
                query = query.limit(filters['limit'])

            people = query.all()

            result = []
            for person in people:
                groups = [group.name for group in person.groups]
                contact_info = {
                    'email': person.contact_info.email if person.contact_info else None,
                    'phone': person.contact_info.phone if person.contact_info else None
                }

                result.append({
                    'id': person.id,
                    'name': person.name,
                    'age': person.age,
                    'groups': groups,
                    'contact_info': contact_info
                })

            return result
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}") from e
        finally:
            session.close()

    def update_person(self, person_id: int, name: str = None, age: int = None) -> bool:
        """Update a person's information"""
        if name is None and age is None:
            raise ValueError("At least one field (name or age) must be provided for update")

        if name is not None and not self._validate_name(name):
            raise ValueError("Name must not be empty and <= 100 characters")
        if age is not None and not self._validate_age(age):
            raise ValueError("Age must be > 0")

        session = self.Session()
        try:
            person = session.query(Person).filter_by(id=person_id).first()
            if not person:
                raise ValueError(f"Person with ID {person_id} not found")

            changes = []
            if name is not None:
                person.name = name.strip()
                changes.append(f"name: {name}")
            if age is not None:
                person.age = age
                changes.append(f"age: {age}")

            session.commit()

            self._log_change(session, "Person", "update",
                             f"Updated person {person_id}: {', '.join(changes)}")
            session.commit()

            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Database error: {str(e)}") from e
        finally:
            session.close()

    def delete_person(self, person_id: int) -> bool:
        """Delete a person and their associated data"""
        session = self.Session()
        try:
            person = session.query(Person).filter_by(id=person_id).first()
            if not person:
                raise ValueError(f"Person with ID {person_id} not found")

            person_name = person.name
            session.delete(person)
            session.commit()

            self._log_change(session, "Person", "delete",
                             f"Deleted person {person_id}: {person_name}")
            session.commit()

            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Database error: {str(e)}") from e
        finally:
            session.close()

    def batch_update_age(self, person_ids: List[int], age: int) -> bool:
        """Update age for multiple people in a single transaction"""
        if not self._validate_age(age):
            raise ValueError("Age must be > 0")

        session = self.Session()
        try:
            # Validate all person IDs exist
            people = session.query(Person).filter(Person.id.in_(person_ids)).all()
            found_ids = {person.id for person in people}
            missing_ids = set(person_ids) - found_ids

            if missing_ids:
                raise ValueError(f"Person(s) with ID(s) {sorted(missing_ids)} not found")

            # Update all people
            for person in people:
                person.age = age

            session.commit()

            self._log_change(session, "Person", "update",
                             f"Batch updated age to {age} for persons: {sorted(person_ids)}")
            session.commit()

            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Database error: {str(e)}") from e
        finally:
            session.close()

    def export_data(self, entity: str, export_format: str, file_path: str) -> bool:
        """Export data to JSON or CSV format"""
        if export_format not in ['json', 'csv']:
            raise ValueError("Format must be 'json' or 'csv'")
        if entity not in ['person', 'group', 'contact']:
            raise ValueError("Entity must be 'person', 'group', or 'contact'")

        session = self.Session()
        try:
            data = []

            if entity == 'person':
                people = session.query(Person).all()
                for person in people:
                    groups = [group.name for group in person.groups]
                    contact_info = person.contact_info
                    data.append({
                        'id': person.id,
                        'name': person.name,
                        'age': person.age,
                        'groups': groups,
                        'email': contact_info.email if contact_info else None,
                        'phone': contact_info.phone if contact_info else None
                    })

            elif entity == 'group':
                groups = session.query(Group).all()
                for group in groups:
                    people = [person.name for person in group.people]
                    data.append({
                        'id': group.id,
                        'name': group.name,
                        'people': people
                    })

            elif entity == 'contact':
                contacts = session.query(ContactInfo).all()
                for contact in contacts:
                    data.append({
                        'id': contact.id,
                        'email': contact.email,
                        'phone': contact.phone,
                        'person_id': contact.person_id,
                        'person_name': contact.person.name
                    })

            # Write to file
            if export_format == 'json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            elif export_format == 'csv':
                if data:
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=data[0].keys())
                        writer.writeheader()
                        writer.writerows(data)

            return True
        except Exception as e:
            raise RuntimeError(f"Export failed: {str(e)}") from e
        finally:
            session.close()

    def import_data(self, entity: str, input_format: str, file_path: str) -> bool:
        """Import data from JSON or CSV format"""
        if input_format not in ['json', 'csv']:
            raise ValueError("Format must be 'json' or 'csv'")
        if entity not in ['person', 'group']:
            raise ValueError("Entity must be 'person' or 'group'")

        try:
            # Read data from file
            if input_format == 'json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            elif input_format == 'csv':
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    data = list(reader)

            session = self.Session()
            try:
                if entity == 'person':
                    for item in data:
                        person = Person(
                            name=item['name'],
                            age=int(item['age'])
                        )
                        session.add(person)
                        session.flush()  # Get the ID

                        if item.get('email'):
                            contact_info = ContactInfo(
                                email=item['email'],
                                phone=item.get('phone'),
                                person_id=person.id
                            )
                            session.add(contact_info)

                elif entity == 'group':
                    for item in data:
                        group = Group(name=item['name'])
                        session.add(group)

                session.commit()
                return True
            except SQLAlchemyError as e:
                session.rollback()
                raise RuntimeError(f"Import failed: {str(e)}") from e
            finally:
                session.close()

        except Exception as e:
            raise RuntimeError(f"Import failed: {str(e)}") from e


def main():
    parser = argparse.ArgumentParser(description="People Management CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Create person
    create_person_parser = subparsers.add_parser('create-person', help='Create a new person')
    create_person_parser.add_argument('--name', required=True, help='Person name')
    create_person_parser.add_argument('--age', type=int, required=True, help='Person age')

    # Add contact
    add_contact_parser = subparsers.add_parser('add-contact', help='Add contact info to a person')
    add_contact_parser.add_argument('--person-id', type=int, required=True, help='Person ID')
    add_contact_parser.add_argument('--email', required=True, help='Email address')
    add_contact_parser.add_argument('--phone', help='Phone number')

    # Create group
    create_group_parser = subparsers.add_parser('create-group', help='Create a new group')
    create_group_parser.add_argument('--name', required=True, help='Group name')

    # Assign group
    assign_group_parser = subparsers.add_parser('assign-group', help='Assign person to group')
    assign_group_parser.add_argument('--person-id', type=int, required=True, help='Person ID')
    assign_group_parser.add_argument('--group-id', type=int, required=True, help='Group ID')

    # Read people
    read_parser = subparsers.add_parser('read', help='Read people with optional filters')
    read_parser.add_argument('--min-age', type=int, help='Minimum age filter')
    read_parser.add_argument('--max-age', type=int, help='Maximum age filter')
    read_parser.add_argument('--name-contains', help='Name contains filter')
    read_parser.add_argument('--group', help='Group name filter')
    read_parser.add_argument('--sort-by', choices=['name', 'age', 'id'], help='Sort by field')
    read_parser.add_argument('--limit', type=int, help='Limit results')
    read_parser.add_argument('--offset', type=int, help='Offset results')

    # Update person
    update_person_parser = subparsers.add_parser('update-person', help='Update person information')
    update_person_parser.add_argument('--id', type=int, required=True, help='Person ID')
    update_person_parser.add_argument('--name', help='New name')
    update_person_parser.add_argument('--age', type=int, help='New age')

    # Delete person
    delete_person_parser = subparsers.add_parser('delete-person', help='Delete a person')
    delete_person_parser.add_argument('--id', type=int, required=True, help='Person ID')

    # Batch update age
    batch_update_parser = subparsers.add_parser('batch-update-age',
                                                help='Batch update age for multiple people')
    batch_update_parser.add_argument('--ids', type=int, nargs='+', required=True, help='Person IDs')
    batch_update_parser.add_argument('--age', type=int, required=True, help='New age')

    # Export
    export_parser = subparsers.add_parser('export', help='Export data')
    export_parser.add_argument('--format', choices=['json', 'csv'],
                               required=True, help='Export format')
    export_parser.add_argument('--entity', choices=['person', 'group', 'contact'],
                               required=True, help='Entity to export')
    export_parser.add_argument('--output', required=True, help='Output file path')

    # Import
    import_parser = subparsers.add_parser('import', help='Import data')
    import_parser.add_argument('--format', choices=['json', 'csv'],
                               required=True, help='Import format')
    import_parser.add_argument('--entity', choices=['person', 'group'],
                               required=True, help='Entity to import')
    import_parser.add_argument('--input', required=True, help='Input file path')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    db = DatabaseManager()

    try:
        if args.command == 'create-person':
            person_id = db.create_person(args.name, args.age)
            print(f"Created Person with ID: {person_id}")

        elif args.command == 'add-contact':
            db.add_or_update_contact(args.person_id, args.email, args.phone)
            print(f"Added ContactInfo to Person ID: {args.person_id}")

        elif args.command == 'create-group':
            group_id = db.create_group(args.name)
            print(f"Created Group with ID: {group_id}")

        elif args.command == 'assign-group':
            db.assign_group(args.person_id, args.group_id)
            print(f"Assigned Person ID: {args.person_id} to Group ID: {args.group_id}")

        elif args.command == 'read':
            filters = {}
            if args.min_age:
                filters['min_age'] = args.min_age
            if args.max_age:
                filters['max_age'] = args.max_age
            if args.name_contains:
                filters['name_contains'] = args.name_contains
            if args.group:
                filters['group'] = args.group
            if args.sort_by:
                filters['sort_by'] = args.sort_by
            if args.limit:
                filters['limit'] = args.limit
            if args.offset:
                filters['offset'] = args.offset

            people = db.read_people(filters)
            for person in people:
                print(f"ID: {person['id']}, Name: {person['name']}, Age: {person['age']}")
                if person['groups']:
                    print(f"Groups: {', '.join(person['groups'])}")

                email = person['contact_info']['email'] or 'None'
                phone = person['contact_info']['phone'] or 'None'
                print(f"Email: {email} | Phone: {phone}")
                print()

        elif args.command == 'update-person':
            db.update_person(args.id, args.name, args.age)
            print(f"Updated Person ID: {args.id}")

        elif args.command == 'delete-person':
            db.delete_person(args.id)
            print(f"Deleted Person ID: {args.id}")

        elif args.command == 'batch-update-age':
            db.batch_update_age(args.ids, args.age)
            print(f"Updated age to {args.age} for Persons: {', '.join(map(str, args.ids))}")

        elif args.command == 'export':
            db.export_data(args.entity, args.format, args.output)
            print(f"Exported records to {args.output}")

        elif args.command == 'import':
            db.import_data(args.entity, args.format, args.input)
            print(f"Imported records from {args.input}")

    except (ValueError, RuntimeError) as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()

