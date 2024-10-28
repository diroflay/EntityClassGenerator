# Database Entity Generator

A Python-based tool that automatically generates C# entity classes from an existing MySQL database. The generator creates properly formatted C# classes with optional data annotations and follows C# naming conventions while maintaining the original database schema mapping.

## Features

- Automatically generates C# entity classes from MySQL database tables
- Configurable through INI file
- Converts snake_case database names to PascalCase C# properties
- Optional data annotations for entity configuration
- Supports all common MySQL data types
- Handles nullable types correctly
- Generates one file per database table
- Customizable output directory and namespace

## Prerequisites

- Python 3.7 or higher
- MySQL database
- Access to database schema

## Installation

1. Clone or download this repository
2. Run the `install_dependencies.bat` file, or manually install the required package:
   ```bash
   pip install mysql-connector-python
   ```

## Configuration

Create a `database_config.ini` file in the same directory as the generator with the following structure:

```ini
[Database]
host = localhost
database = your_database_name
user = root
password = your_password

[Generator]
output_directory = ./Entities
namespace = YourNamespace

[Attributes]
# Enable or disable specific attributes
use_key_attribute = true
use_required_attribute = true
use_column_attribute = true
use_maxlength_attribute = true
use_table_attribute = true
use_databasegenerated_attribute = true
```

### Configuration Options

#### Database Section
- `host`: Database server address
- `database`: Name of the database to generate entities from
- `user`: Database username
- `password`: Database password

#### Generator Section
- `output_directory`: Where the generated files will be saved
- `namespace`: The namespace for the generated C# classes

#### Attributes Section
- `use_key_attribute`: Generate [Key] attribute for primary keys
- `use_required_attribute`: Generate [Required] attribute for non-nullable fields
- `use_column_attribute`: Generate [Column] attribute for property-column mapping
- `use_maxlength_attribute`: Generate [MaxLength] attribute for string fields
- `use_table_attribute`: Generate [Table] attribute for class-table mapping
- `use_databasegenerated_attribute`: Generate [DatabaseGenerated] attribute for auto-increment fields

## Usage

1. Configure your database connection in `database_config.ini`
2. Run the generator using the `run.bat` file, or manually:
   ```bash
   python entity_generator.py
   ```

The generator will create C# entity classes in the specified output directory.

## Example Output

For a database table named `user_accounts`:

```csharp
using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace YourNamespace
{
    [Table("user_accounts")]
    public class UserAccounts
    {
        [Key]
        [DatabaseGenerated(DatabaseGeneratedOption.Identity)]
        [Column("user_id")]
        public int UserId { get; set; }

        [Required]
        [Column("username")]
        [MaxLength(50)]
        public string Username { get; set; }

        [Column("last_login")]
        public DateTime? LastLogin { get; set; }

        [Column("is_active")]
        public bool IsActive { get; set; }
    }
}
```

## Type Mapping

The generator maps MySQL data types to C# types as follows:

- `bit` → `bool`
- `tinyint` → `byte` (or `bool` for tinyint(1))
- `smallint` → `short`
- `int` → `int`
- `bigint` → `long`
- `decimal` → `decimal`
- `float` → `float`
- `double` → `double`
- `datetime` → `DateTime`
- `date` → `DateTime`
- `time` → `TimeSpan`
- `char` → `string`
- `varchar` → `string`
- `text` → `string`
- `json` → `string`

## Files in the Project

- `entity_generator.py`: Main generator script
- `database_config.ini`: Configuration file
- `install_dependencies.bat`: Script to install required Python packages
- `run.bat`: Script to run the generator
- `README.md`: This documentation file

## Common Issues

1. **Connection Error**: Ensure your MySQL server is running and the credentials in `database_config.ini` are correct.

2. **Missing Tables**: Verify that:
   - The specified database exists
   - Your user has permission to access the schema
   - The database contains tables

3. **Output Directory**: If the specified output directory doesn't exist, the generator will create it automatically.

## Customization

The generator can be customized by:

1. Modifying the configuration file
2. Adjusting attribute generation options
3. Changing the output directory structure
4. Modifying the namespace convention

## Limitations

- Currently supports MySQL databases only
- Generates only entity classes (no DbContext)
- Does not handle table relationships automatically

## Error Handling

The generator includes error handling for:
- Missing configuration file
- Invalid database connections
- Missing required configuration parameters
- Database access errors
- File system errors

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.
