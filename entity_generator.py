import mysql.connector
from mysql.connector import Error
import os
from typing import List, Dict, Optional
import re
from dataclasses import dataclass
import configparser
import sys
from pathlib import Path
from datetime import datetime

@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool
    is_auto_increment: bool
    max_length: Optional[int]
    numeric_precision: Optional[int]
    numeric_scale: Optional[int]

@dataclass
class AttributeConfig:
    use_key: bool = True
    use_required: bool = True
    use_column: bool = True
    use_maxlength: bool = True
    use_table: bool = True
    use_database_generated: bool = True

class ConfigurationError(Exception):
    """Custom exception for configuration errors"""
    pass

# ... (previous imports remain the same)

class EntityGenerator:
    def __init__(self, config_file: str):
        self.config = self._load_configuration(config_file)
        self.output_dir = self.config['Generator']['output_directory']
        self.attribute_config = self._load_attribute_config()
        self.verbose = self.config['Generator'].getboolean('verbose', True)
        self.generate_sql = self.config['Generator'].getboolean('generate_sql', False)
        self.sql_output_file = self.config['Generator'].get('sql_output_file', 'database_structure.sql')
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        self.log("Initialized generator with configuration from: " + config_file)
    
    def log(self, message: str):
        """Print message if verbose mode is enabled"""
        if self.verbose:
            print(message)

    async def generate_sql_script(self, cursor) -> str:
        """Generate SQL creation script for all tables"""
        self.log("Generating SQL creation script...")
        
        tables = await self.get_tables(cursor)
        script_parts = []
        
        # Add header
        script_parts.extend([
            "-- Database structure script",
            f"-- Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"-- Database: {self.config['Database']['database']}",
            "",
            "SET FOREIGN_KEY_CHECKS=0;",
            "SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';",
            "SET NAMES utf8mb4;",
            ""
        ])

        for table in tables:
            self.log(f"Getting structure for table: {table}")
            
            # Get table creation SQL
            cursor.execute(f"SHOW CREATE TABLE `{table}`")
            create_table_sql = cursor.fetchone()[1]
            
            # Add to script
            script_parts.extend([
                f"-- Table structure for table `{table}`",
                "DROP TABLE IF EXISTS `" + table + "`;",
                create_table_sql + ";",
                ""
            ])

        script_parts.append("SET FOREIGN_KEY_CHECKS=1;")
        
        return "\n".join(script_parts)

    async def generate_entities(self):
        """Main method to generate all entity classes"""
        try:
            self.log("Connecting to database...")
            conn = self.get_connection()
            self.log(f"Successfully connected to database: {self.config['Database']['database']}")
            
            cursor = conn.cursor()
            
            # Get all tables
            tables = await self.get_tables(cursor)
            self.log(f"Found {len(tables)} tables in database")
            
            # Generate SQL script if requested
            if self.generate_sql:
                self.log("Generating SQL script...")
                sql_script = await self.generate_sql_script(cursor)
                sql_file_path = os.path.join(self.output_dir, self.sql_output_file)
                
                with open(sql_file_path, 'w', encoding='utf-8') as f:
                    f.write(sql_script)
                self.log(f"SQL script generated: {sql_file_path}")
            
            # Generate class for each table
            for table in tables:
                self.log(f"Processing table: {table}")
                
                # Get columns for this table
                columns = await self.get_columns(cursor, table)
                self.log(f"Found {len(columns)} columns in table {table}")
                
                # Generate class content
                class_content = self.generate_class(table, columns)
                
                # Write to file
                file_name = f"{self.to_pascal_case(table)}.cs"
                file_path = os.path.join(self.output_dir, file_name)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(class_content)
                
                self.log(f"Generated entity class: {file_name}")
            
            self.log("\nEntity generation completed successfully!")
            
        except Error as e:
            self.log(f"Database error: {e}")
            raise
        except Exception as e:
            self.log(f"Error: {e}")
            raise
        finally:
            if 'conn' in locals():
                cursor.close()
                conn.close()
                self.log("Database connection closed")

    def get_connection(self):
        """Create database connection using configuration"""
        try:
            conn = mysql.connector.connect(
                host=self.config['Database']['host'],
                database=self.config['Database']['database'],
                user=self.config['Database']['user'],
                password=self.config['Database']['password']
            )
            return conn
        except Error as e:
            self.log(f"Failed to connect to database: {e}")
            raise
    
    def _load_attribute_config(self) -> AttributeConfig:
        """Load attribute configuration with defaults"""
        attr_config = self.config['Attributes'] if 'Attributes' in self.config else {}
        
        return AttributeConfig(
            use_key=attr_config.getboolean('use_key_attribute', True),
            use_required=attr_config.getboolean('use_required_attribute', True),
            use_column=attr_config.getboolean('use_column_attribute', True),
            use_maxlength=attr_config.getboolean('use_maxlength_attribute', True),
            use_table=attr_config.getboolean('use_table_attribute', True),
            use_database_generated=attr_config.getboolean('use_databasegenerated_attribute', True)
        )
    
    def _load_configuration(self, config_file: str) -> configparser.ConfigParser:
        """Load and validate configuration from INI file"""
        if not os.path.exists(config_file):
            raise ConfigurationError(f"Configuration file not found: {config_file}")
        
        config = configparser.ConfigParser()
        config.read(config_file)
        
        # Validate required sections
        required_sections = ['Database', 'Generator']
        for section in required_sections:
            if section not in config:
                raise ConfigurationError(f"Missing required section: {section}")
        
        # Validate Database section
        required_db_params = ['host', 'database', 'user', 'password']
        for param in required_db_params:
            if param not in config['Database']:
                raise ConfigurationError(f"Missing required database parameter: {param}")
        
        # Validate Generator section
        required_gen_params = ['output_directory', 'namespace']
        for param in required_gen_params:
            if param not in config['Generator']:
                raise ConfigurationError(f"Missing required generator parameter: {param}")
        
        return config

    def generate_class(self, table_name: str, columns: List[ColumnInfo]) -> str:
        """Generate C# class content"""
        class_name = self.to_pascal_case(table_name)
        
        # Collect necessary using statements
        using_statements = set(["using System;"])
        
        if any([self.attribute_config.use_key, self.attribute_config.use_required,
                self.attribute_config.use_maxlength]):
            using_statements.add("using System.ComponentModel.DataAnnotations;")
        
        if any([self.attribute_config.use_column, self.attribute_config.use_table,
                self.attribute_config.use_database_generated]):
            using_statements.add("using System.ComponentModel.DataAnnotations.Schema;")
        
        lines = list(sorted(using_statements))
        lines.extend(["", f"namespace {self.config['Generator']['namespace']}", "{"])
        
        # Add table attribute if configured
        if self.attribute_config.use_table:
            lines.append(f'    [Table("{table_name}")]')
        
        lines.extend([
            f"    public class {class_name}",
            "    {"
        ])
        
        # Add properties
        for column in columns:
            attributes = []
            
            # Add Key attribute
            if column.is_primary_key and self.attribute_config.use_key:
                attributes.append("        [Key]")
            
            # Add DatabaseGenerated attribute
            if column.is_auto_increment and self.attribute_config.use_database_generated:
                attributes.append("        [DatabaseGenerated(DatabaseGeneratedOption.Identity)]")
            
            # Add Column attribute
            if self.attribute_config.use_column:
                attributes.append(f'        [Column("{column.name}")]')
            
            # Add Required attribute
            if not column.is_nullable and column.data_type != "string" and self.attribute_config.use_required:
                attributes.append("        [Required]")
            
            # Add MaxLength for string fields
            if (column.max_length and column.data_type in ['varchar', 'char'] 
                and self.attribute_config.use_maxlength):
                attributes.append(f"        [MaxLength({column.max_length})]")
            
            # Add attributes if any
            if attributes:
                lines.extend(attributes)
            
            # Add property
            property_type = self.get_csharp_type(column)
            property_name = self.to_pascal_case(column.name)
            lines.append(f"        public {property_type} {property_name} {{ get; set; }}")
            lines.append("")
        
        # Close class and namespace
        lines.extend(["    }", "}"])
        
        return "\n".join(lines)
    
    def to_pascal_case(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase"""
        return ''.join(word.title() for word in snake_str.split('_'))
    
    def get_csharp_type(self, column: ColumnInfo) -> str:
        """Map MySQL types to C# types with special handling for boolean fields"""
        base_type = column.data_type.lower()
        
        # Special handling for tinyint(1) which represents boolean in MySQL
        if base_type == 'tinyint' and column.max_length == 1:
            return 'bool' if not column.is_nullable else 'bool?'
            
        type_mapping = {
            'bit': 'bool',
            'tinyint': 'byte',
            'smallint': 'short',
            'int': 'int',
            'bigint': 'long',
            'decimal': 'decimal',
            'float': 'float',
            'double': 'double',
            'datetime': 'DateTime',
            'date': 'DateTime',
            'timestamp': 'DateTime',
            'time': 'TimeSpan',
            'char': 'string',
            'varchar': 'string',
            'text': 'string',
            'longtext': 'string',
            'json': 'string'
        }
        
        cs_type = type_mapping.get(base_type, 'object')
        if column.is_nullable and cs_type != 'string':
            return f"{cs_type}?"
        return cs_type

    async def get_columns(self, cursor, table_name: str) -> List[ColumnInfo]:
        """Get column information for a table with enhanced type information"""
        cursor.execute("""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_KEY,
                EXTRA,
                CHARACTER_MAXIMUM_LENGTH,
                NUMERIC_PRECISION,
                NUMERIC_SCALE,
                COLUMN_TYPE  -- Added to get full type information including length
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """, (self.config['Database']['database'], table_name))
        
        columns = []
        for row in cursor.fetchall():
            # Extract length from COLUMN_TYPE for tinyint
            column_type = row[8].lower()  # e.g., "tinyint(1)"
            max_length = None
            
            if "tinyint" in column_type:
                # Extract the length from tinyint(n)
                match = re.search(r'tinyint\((\d+)\)', column_type)
                if match:
                    max_length = int(match.group(1))
            else:
                max_length = row[5]  # Use CHARACTER_MAXIMUM_LENGTH for other types
            
            columns.append(ColumnInfo(
                name=row[0],
                data_type=row[1],
                is_nullable=row[2] == "YES",
                is_primary_key=row[3] == "PRI",
                is_auto_increment="auto_increment" in row[4],
                max_length=max_length,
                numeric_precision=row[6],
                numeric_scale=row[7]
            ))
        
        return columns
    
    async def get_tables(self, cursor) -> List[str]:
        """Get all tables from the database"""
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
        """, (self.config['Database']['database'],))
        
        return [row[0] for row in cursor.fetchall()]
    

def create_default_config(file_path: str):
    """Create a default configuration file"""
    config = configparser.ConfigParser()
    
    config['Database'] = {
        'host': 'localhost',
        'database': 'your_database_name',
        'user': 'username',
        'password': 'your_password'
    }
    
    config['Generator'] = {
        'output_directory': './GeneratedEntities',
        'namespace': 'Write.Your.Namespace',
        'language': 'csharp'
    }
    
    config['Attributes'] = {
        'use_key_attribute': 'true',
        'use_required_attribute': 'true',
        'use_column_attribute': 'true',
        'use_maxlength_attribute': 'true',
        'use_table_attribute': 'true',
        'use_databasegenerated_attribute': 'true'
    }
    
    with open(file_path, 'w') as config_file:
        config.write(config_file)


def main():
    print("Database Entity Generator")
    print("------------------------")
    
    # Check if config file is provided as argument
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = 'database_config.ini'
    
    # If config file doesn't exist, create a default one
    if not os.path.exists(config_file):
        print(f"Configuration file not found. Creating default configuration at: {config_file}")
        create_default_config(config_file)
        print("Please update the configuration file with your database details and run the program again.")
        return
    
    try:
        # Create generator instance with config
        generator = EntityGenerator(config_file)
        
        # Run generator
        import asyncio
        asyncio.run(generator.generate_entities())
        
    except ConfigurationError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Error: {e}")



if __name__ == "__main__":
    main()