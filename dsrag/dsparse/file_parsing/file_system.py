import os
from ..utils.imports import boto3
import io
import json
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime


class FileSystem(ABC):
    subclasses = {}

    def __init__(self, base_path: str):
        self.base_path = base_path

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.subclasses[cls.__name__] = cls

    def to_dict(self):
        return {
            "subclass_name": self.__class__.__name__,
            "base_path": self.base_path
        }

    @classmethod
    def from_dict(cls, config):
        subclass_name = config.pop(
            "subclass_name", None
        )  # Remove subclass_name from config
        subclass = cls.subclasses.get(subclass_name)
        if subclass:
            return subclass(**config)  # Pass the modified config without subclass_name
        else:
            raise ValueError(f"Unknown subclass: {subclass_name}")

    @abstractmethod
    def create_directory(self, kb_id: str, doc_id: str) -> None:
        pass

    @abstractmethod
    def delete_directory(self, kb_id: str, doc_id: str) -> None:
        pass

    @abstractmethod
    def delete_kb(self, kb_id: str) -> None:
        pass

    @abstractmethod
    def save_json(self, kb_id: str, doc_id: str, file_name: str, file: dict) -> None:
        pass

    @abstractmethod
    def save_image(self, kb_id: str, doc_id: str, file_name: str, file: any) -> None:
        pass

    @abstractmethod
    def get_files(self, kb_id: str, doc_id: str, page_start: int, page_end: int) -> List[str]:
        pass

    @abstractmethod
    def get_all_jpg_files(self, kb_id: str, doc_id: str) -> List[str]:
        pass

    @abstractmethod
    def log_error(self, kb_id: str, doc_id: str, error: dict) -> None:
        pass

    @abstractmethod
    def save_page_content(self, kb_id: str, doc_id: str, page_number: int, content: str) -> None:
        """Save the text content of a page to a JSON file"""
        pass

    @abstractmethod
    def load_page_content(self, kb_id: str, doc_id: str, page_number: int) -> Optional[str]:
        """Load the text content of a page from its JSON file"""
        pass

    @abstractmethod
    def load_page_content_range(self, kb_id: str, doc_id: str, page_start: int, page_end: int) -> list[str]:
        """Load the text content for a range of pages"""
        pass

    @abstractmethod
    def load_data(self, kb_id: str, doc_id: str, data_name: str) -> Optional[dict]:
        """Load JSON data from a file
        Args:
            kb_id: Knowledge base ID
            doc_id: Document ID 
            data_name: Name of the data to load (e.g. "elements" for elements.json)
        """
        pass


class LocalFileSystem(FileSystem):
    """
    Uses the local file system to store and retrieve page image files and other data.
    """
    def __init__(self, base_path: str):
        super().__init__(base_path)

    def create_directory(self, kb_id: str, doc_id: str) -> None:
        """
        Create a directory to store the images of the pages
        """
        page_images_path = os.path.join(self.base_path, kb_id, doc_id)
        if os.path.exists(page_images_path):
            for file in os.listdir(page_images_path):
                os.remove(os.path.join(page_images_path, file))
            os.rmdir(page_images_path)

        # Create the folder
        os.makedirs(page_images_path, exist_ok=False)

    def delete_directory(self, kb_id: str, doc_id: str) -> None:
        """
        Delete the directory
        """
        page_images_path = os.path.join(self.base_path, kb_id, doc_id)

        # make sure the path exists and is a directory
        if os.path.exists(page_images_path) and os.path.isdir(page_images_path):
            for file in os.listdir(page_images_path):
                os.remove(os.path.join(page_images_path, file))
            os.rmdir(page_images_path)

    def delete_kb(self, kb_id: str) -> None:
        """
        Delete the knowledge base
        """
        kb_path = os.path.join(self.base_path, kb_id)
        if os.path.exists(kb_path):
            for doc_id in os.listdir(kb_path):
                self.delete_directory(kb_id, doc_id)
            self.delete_directory(kb_id, "")

    def save_json(self, kb_id: str, doc_id: str, file_name: str, file: dict) -> None:
        """
        Save the file to the local system
        """

        file_path = os.path.join(self.base_path, kb_id, doc_id, file_name)
        with open(file_path, "w") as f:
            json.dump(file, f, indent=2)
        
    def save_image(self, kb_id: str, doc_id: str, file_name: str, image: any) -> None:
        """
        Save the image to the local system
        """
        image_path = os.path.join(self.base_path, kb_id, doc_id, file_name)
        image.save(image_path)

    def get_files(self, kb_id: str, doc_id: str, page_start: int, page_end: int) -> List[str]:
        """
        Get the file from the local system
        - page_start: int - the starting page number
        - page_end: int - the ending page number (inclusive)
        """
        if page_start is None or page_end is None:
            return []
        page_images_path = os.path.join(self.base_path, kb_id, doc_id)
        image_file_paths = []
        
        # Try multiple extensions for backward compatibility, but only return first found per page
        for i in range(page_start, page_end + 1):
            for ext in ['.jpg', '.jpeg', '.png']:  # Try in order of preference
                image_file_path = os.path.join(page_images_path, f'page_{i}{ext}')
                if os.path.exists(image_file_path):
                    image_file_paths.append(image_file_path)
                    break  # Found the file, no need to check other extensions
                    
        return image_file_paths
    
    def get_all_jpg_files(self, kb_id: str, doc_id: str) -> List[str]:
        """
        Same as get_files except it returns all the files instead of just those in a page range
        """
        page_images_path = os.path.join(self.base_path, kb_id, doc_id)
        image_file_paths = []
        for file in os.listdir(page_images_path):
            # Make sure the file is an image (support multiple formats for backward compatibility)
            if not (file.endswith('.jpg') or file.endswith('.jpeg') or file.endswith('.png')):
                continue
            image_file_paths.append(os.path.join(page_images_path, file))

        # Sort the files by page number
        image_file_paths.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]))
        return image_file_paths
    
    def log_error(self, kb_id: str, doc_id: str, error: dict) -> None:
        pass

    def save_page_content(self, kb_id: str, doc_id: str, page_number: int, content: str) -> None:
        """Save the text content of a page to a JSON file"""
        page_content_path = os.path.join(self.base_path, kb_id, doc_id, f'page_content_{page_number}.json')
        with open(page_content_path, 'w') as f:
            json.dump({"content": content}, f)

    def load_page_content(self, kb_id: str, doc_id: str, page_number: int) -> Optional[str]:
        """Load the text content of a page from its JSON file"""
        page_content_path = os.path.join(self.base_path, kb_id, doc_id, f'page_content_{page_number}.json')
        try:
            with open(page_content_path, 'r') as f:
                data = json.load(f)
                return data["content"]
        except FileNotFoundError:
            return None

    def load_page_content_range(self, kb_id: str, doc_id: str, page_start: int, page_end: int) -> list[str]:
        """Load the text content for a range of pages"""
        page_contents = []
        for page_num in range(page_start, page_end + 1):
            content = self.load_page_content(kb_id, doc_id, page_num)
            if content is not None:
                page_contents.append(content)
        return page_contents

    def load_data(self, kb_id: str, doc_id: str, data_name: str) -> Optional[dict]:
        """Load JSON data from a file in the local filesystem"""
        file_path = os.path.join(self.base_path, kb_id, doc_id, f"{data_name}.json")
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"File not found: {file_path}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {file_path}: {str(e)}")
            return None


class S3FileSystem(FileSystem):
    """
    Uses S3 and DynamoDB to store and retrieve page image files and other data.
    """
    def __init__(self, base_path: str, bucket_name: str, region_name: str, access_key: str, secret_key: str, error_table: str = None, dynamodb_table_name: str = None, dynamodb_client_data_table_name: str = None):
        super().__init__(base_path)
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.access_key = access_key
        self.secret_key = secret_key
        self.error_table = error_table
        self.dynamodb_table_name = dynamodb_table_name
        self.dynamodb_client_data_table_name = dynamodb_client_data_table_name

    def create_s3_client(self):
        return boto3.client(
            service_name='s3',
            region_name=self.region_name,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        )

    def create_directory(self, kb_id: str, doc_id: str) -> None:
        """
        This function is not needed for S3
        """
        pass

    def delete_directory(self, kb_id: str, doc_id: str) -> List[dict]:
        """
        Delete the directory in S3. Used when deleting a document.
        """
        
        s3_client = self.create_s3_client()
        prefix = f"{kb_id}/{doc_id}/"

        # List all objects with the specified prefix
        response = s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)

        # Check if there are any objects to delete
        if 'Contents' in response:
            # Prepare a list of object keys to delete
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]

            # Delete the objects
            s3_client.delete_objects(Bucket=self.bucket_name, Delete={'Objects': objects_to_delete})
            print(f"Deleted all objects in {prefix} from {self.bucket_name}.")
        else:
            print(f"No objects found in {prefix}.")
            objects_to_delete = []

        return objects_to_delete
    

    def delete_kb(self, kb_id: str) -> None:
        """
        Delete the knowledge base
        """
        s3_client = self.create_s3_client()
        prefix = f"{kb_id}/"

        # List all objects with the specified prefix
        response = s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
        # Check if there are any objects to delete
        if 'Contents' in response:
            # Prepare a list of object keys to delete
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]

            # Delete the objects
            s3_client.delete_objects(Bucket=self.bucket_name, Delete={'Objects': objects_to_delete})
            print(f"Deleted all objects in {prefix} from {self.bucket_name}.")
        else:
            print(f"No objects found in {prefix}.")
            objects_to_delete = []
        
        return objects_to_delete


    def save_json(self, kb_id: str, doc_id: str, file_name: str, file: dict) -> None:
        """
        Save the JSON file to S3
        """

        file_name = f"{kb_id}/{doc_id}/{file_name}"
        json_data = json.dumps(file, indent=2)  # Serialize the JSON data

        s3_client = self.create_s3_client()
        try:
            s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=json_data,
                ContentType='application/json'
            )
            print(f"JSON data uploaded to {self.bucket_name}/{file_name}.")
        except Exception as e:
            raise RuntimeError(f"Failed to upload JSON to S3.") from e

    def save_image(self, kb_id: str, doc_id: str, file_name: str, file: any) -> None:
        """
        Upload the file to S3
        """
        file_name = f"{kb_id}/{doc_id}/{file_name}"
        buffer = io.BytesIO()
        file.save(buffer, format='JPEG')
        buffer.seek(0)  # Rewind the buffer to the beginning

        s3_client = self.create_s3_client()
        try:
            s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=buffer,
                ContentType='image/jpeg'
            )
            print(f"JPEG uploaded to {self.bucket_name}/{file_name}.")
        except Exception as e:
            raise RuntimeError(f"Failed to upload image to S3.") from e


    def get_files(self, kb_id: str, doc_id: str, page_start: int, page_end: int) -> List[str]:
        """
        Get the file from S3
        - page_start: int - the starting page number
        - page_end: int - the ending page number (inclusive)
        """
        if page_start is None or page_end is None:
            return []
        
        s3_client = self.create_s3_client()
        file_paths = []
        
        # Try multiple extensions for backward compatibility, but only return first found per page
        for i in range(page_start, page_end + 1):
            found_file = False
            for ext in ['.jpg', '.jpeg', '.png']:  # Try in order of preference
                filename = f"{kb_id}/{doc_id}/page_{i}{ext}"
                output_folder = os.path.join(self.base_path, kb_id, doc_id)
                if not os.path.exists(output_folder):
                    try:
                        os.makedirs(output_folder)
                    except FileExistsError:
                        # Since this function can be called in parallel, the folder may have been created by another process
                        pass
                output_filepath = os.path.join(self.base_path, filename)
                try:
                    s3_client.download_file(
                        self.bucket_name,
                        filename,
                        output_filepath
                    )
                    file_paths.append(output_filepath)
                    found_file = True
                    break  # Found file for this page, don't try other extensions
                except Exception as e:
                    # File doesn't exist with this extension, try next extension
                    continue
            
            if not found_file:
                print(f"Warning: No image file found for page {i} in S3")
            
        return file_paths
    
    def get_all_jpg_files(self, kb_id: str, doc_id: str) -> List[str]:
        """
        Get all JPG files from a specific S3 directory and download them to local storage.
        Returns a sorted list of local file paths.
        
        Args:
            kb_id (str): Knowledge base ID
            doc_id (str): Document ID
            
        Returns:
            List[str]: Sorted list of local file paths for the downloaded images
        """
        prefix = f"{kb_id}/{doc_id}/"
        s3_client = self.create_s3_client()
        
        try:
            # List all objects with the specified prefix
            response = s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return []
            
            # Filter for image files (support multiple formats for backward compatibility)
            jpg_files = [obj['Key'] for obj in response['Contents'] 
                        if obj['Key'].lower().endswith(('.jpg', '.jpeg', '.png'))]
            
            # Create local directory if it doesn't exist
            output_folder = os.path.join(self.base_path, kb_id, doc_id)
            os.makedirs(output_folder, exist_ok=True)
            
            # Download each file
            local_file_paths = []
            for s3_key in jpg_files:
                local_path = os.path.join(self.base_path, s3_key)
                try:
                    s3_client.download_file(
                        self.bucket_name,
                        s3_key,
                        local_path
                    )
                    local_file_paths.append(local_path)
                except Exception as e:
                    print(f"Error downloading file {s3_key}: {e}")
                    continue
            
            # Sort the files by page number, similar to LocalFileSystem
            local_file_paths.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]))
            return local_file_paths
            
        except Exception as e:
            print(f"Error listing/downloading files from S3: {e}")
            return []
        
    
    def log_error(self, kb_id: str, doc_id: str, error: dict) -> None:
        if self.error_table is None:
            return
        
        # Create a uuid for this error
        timestamp = datetime.now().isoformat()
        dynamodb_client = boto3.resource(
            'dynamodb',
            region_name=self.region_name,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        )
        table = dynamodb_client.Table(self.error_table)
        item = {
            'client_id': kb_id,
            'doc_id': doc_id,
            'error': error,
            'timestamp': timestamp
        }
        table.put_item(Item=item) 

    def save_page_content(self, kb_id: str, doc_id: str, page_number: int, content: str) -> None:
        """Save the text content of a page to S3"""
        file_name = f"{kb_id}/{doc_id}/page_content_{page_number}.json"
        data = json.dumps({"content": content})

        s3_client = self.create_s3_client()
        try:
            s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=data,
                ContentType='application/json'
            )
        except Exception as e:
            raise RuntimeError(f"Failed to upload page content to S3.") from e

    def load_page_content(self, kb_id: str, doc_id: str, page_number: int) -> Optional[str]:
        """Load the text content of a page from S3"""
        file_name = f"{kb_id}/{doc_id}/page_content_{page_number}.json"
        s3_client = self.create_s3_client()
        
        try:
            response = s3_client.get_object(Bucket=self.bucket_name, Key=file_name)
            data = json.loads(response['Body'].read().decode('utf-8'))
            return data["content"]
        except s3_client.exceptions.NoSuchKey:
            return None
        except Exception as e:
            print(f"Error loading page content from S3: {e}")
            return None

    def load_page_content_range(self, kb_id: str, doc_id: str, page_start: int, page_end: int) -> list[str]:
        """Load the text content for a range of pages from S3"""
        page_contents = []
        for page_num in range(page_start, page_end + 1):
            content = self.load_page_content(kb_id, doc_id, page_num)
            if content is not None:
                page_contents.append(content)
        return page_contents
    
    def to_dict(self):
        base_dict = super().to_dict()
        base_dict.update({
            "bucket_name": self.bucket_name,
            "region_name": self.region_name,
            "access_key": self.access_key,
            "secret_key": self.secret_key,
            "error_table": self.error_table
        })
        return base_dict

    def load_data(self, kb_id: str, doc_id: str, data_name: str) -> Optional[dict]:
        """Load JSON data from a file in S3"""
        s3_key = f"{kb_id}/{doc_id}/{data_name}.json"
        s3_client = self.create_s3_client()
        
        try:
            response = s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return json.loads(response['Body'].read().decode('utf-8'))
        except s3_client.exceptions.NoSuchKey:
            print(f"File not found in S3: {s3_key}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from S3 file {s3_key}: {str(e)}")
            return None
        except Exception as e:
            print(f"Error loading data from S3: {str(e)}")
            return None