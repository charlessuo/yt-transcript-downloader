"""
Comprehensive encoding tests for Chinese and English character handling.
Tests the entire workflow from JSON reading/writing to transcript file generation.
"""
import json
import os
import tempfile
import pytest
from main import (
    load_content_resources,
    save_content_resources,
    generate_filename,
    sanitize_creator_name,
    format_date
)


class TestChineseEnglishEncoding:
    """Test encoding for Chinese and English characters."""

    def test_chinese_creator_name_in_filename(self):
        """Test that Chinese characters in creator names are preserved in filenames."""
        chinese_creators = [
            "海伦子Hellen",
            "Money or Life 美股频道",
            "中文频道",
            "English Channel 中文",
        ]

        for creator in chinese_creators:
            filename = generate_filename("01-08-2026", creator, "test123")
            # Verify Chinese characters are preserved
            assert creator.replace(" ", "_") in filename
            # Verify filename is properly formatted
            assert filename.startswith("01082026_")
            assert filename.endswith("_test123.txt")

    def test_json_read_write_chinese_characters(self):
        """Test that Chinese characters survive JSON read/write cycle."""
        test_data = {
            "content_resources": [
                {
                    "content_creator": "海伦子Hellen",
                    "native_lang": "zh",
                    "content_collection": [
                        {
                            "video_title": "上市即巅峰?解析不同阶段入局SpaceX的机会与风险",
                            "video_id": "inXOHNc_UUo",
                            "published_time": "12-19-2025",
                            "behind_paywall": False,
                            "downloaded": False
                        }
                    ]
                },
                {
                    "content_creator": "Money or Life 美股频道",
                    "native_lang": "zh",
                    "content_collection": [
                        {
                            "video_title": "English and 中文 Mixed Title",
                            "video_id": "test456",
                            "published_time": "01-15-2026",
                            "behind_paywall": False,
                            "downloaded": True
                        }
                    ]
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            temp_file = f.name

        try:
            # Save data
            save_content_resources(test_data, temp_file)

            # Read data back
            loaded_data = load_content_resources(temp_file)

            # Verify Chinese characters are preserved exactly
            assert loaded_data == test_data
            assert loaded_data['content_resources'][0]['content_creator'] == "海伦子Hellen"
            assert loaded_data['content_resources'][1]['content_creator'] == "Money or Life 美股频道"
            assert "上市即巅峰" in loaded_data['content_resources'][0]['content_collection'][0]['video_title']
            assert "中文" in loaded_data['content_resources'][1]['content_collection'][0]['video_title']

            # Verify the file itself contains Chinese characters (not escaped)
            with open(temp_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
                assert "海伦子Hellen" in file_content
                assert "美股频道" in file_content
                assert "上市即巅峰" in file_content
                # Ensure characters are not escaped (should not contain \u escapes for Chinese)
                assert "\\u" not in file_content or file_content.count("\\u") == 0
        finally:
            os.unlink(temp_file)

    def test_mixed_language_video_titles(self):
        """Test that mixed Chinese and English video titles are handled correctly."""
        mixed_titles = [
            "上市即巅峰?解析不同阶段入局SpaceX的机会与风险",
            "Rocket Lab投资者的焦虑—太空物流如何破价格战?",
            "用最啰嗦的方式去火星, New Glenn的成功与商业太空的竞争",
            "English Title with 中文字符 Mixed In",
            "100% English Title",
            "百分百中文标题"
        ]

        test_data = {
            "content_resources": [
                {
                    "content_creator": "Test Creator",
                    "native_lang": "zh",
                    "content_collection": [
                        {
                            "video_title": title,
                            "video_id": f"test{i}",
                            "published_time": "01-08-2026",
                            "behind_paywall": False,
                            "downloaded": False
                        }
                        for i, title in enumerate(mixed_titles)
                    ]
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            temp_file = f.name

        try:
            save_content_resources(test_data, temp_file)
            loaded_data = load_content_resources(temp_file)

            # Verify all titles are preserved correctly
            for i, title in enumerate(mixed_titles):
                assert loaded_data['content_resources'][0]['content_collection'][i]['video_title'] == title
        finally:
            os.unlink(temp_file)

    def test_transcript_file_with_chinese_content(self):
        """Test that Chinese content can be written to and read from transcript files."""
        test_transcript_entries = [
            {"text": "这是中文文本", "start": 0.0, "duration": 2.5},
            {"text": "This is English text", "start": 2.5, "duration": 3.0},
            {"text": "混合 Mixed 内容 Content", "start": 5.5, "duration": 2.0},
            {"text": "SpaceX的星舰发射成功", "start": 7.5, "duration": 3.5},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate a filename with Chinese characters
            filename = generate_filename("12-19-2025", "海伦子Hellen", "test_video")
            output_path = os.path.join(temp_dir, filename)

            # Write transcript (simulating what download_transcript does)
            with open(output_path, 'w', encoding='utf-8') as f:
                for entry in test_transcript_entries:
                    text = entry['text']
                    start_time = entry['start']
                    duration = entry['duration']
                    f.write(f"[{start_time:.2f}s - {start_time + duration:.2f}s] {text}\n")

            # Verify file was created with Chinese characters in the name
            assert os.path.exists(output_path)
            assert "海伦子Hellen" in filename

            # Read back and verify content
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Verify all text is preserved
            assert "这是中文文本" in content
            assert "This is English text" in content
            assert "混合 Mixed 内容 Content" in content
            assert "SpaceX的星舰发射成功" in content

            # Verify timestamps are preserved
            assert "[0.00s - 2.50s]" in content
            assert "[2.50s - 5.50s]" in content

    def test_special_chinese_characters_and_punctuation(self):
        """Test that special Chinese punctuation and characters are handled correctly."""
        special_cases = [
            "上市即巅峰?解析不同阶段",  # Chinese question mark
            "焦虑—太空物流",  # Em dash
            "100%成功率",  # Percent sign with Chinese
            "《星际探索》",  # Chinese quotation marks
            "【重要】通知",  # Chinese brackets
            "价格：$100",  # Chinese colon with dollar sign
        ]

        for text in special_cases:
            # Test in creator name
            sanitized = sanitize_creator_name(text)
            assert len(sanitized) > 0

            # Test in filename generation
            filename = generate_filename("01-08-2026", text, "test123")
            assert "01082026" in filename
            assert "test123.txt" in filename

    def test_file_system_compatibility(self):
        """Test that generated filenames with Chinese characters work on the file system."""
        test_cases = [
            ("海伦子Hellen", "12-19-2025", "inXOHNc_UUo"),
            ("Money or Life 美股频道", "06-14-2025", "t7XX6-pon8M"),
            ("纯中文频道名称", "01-01-2026", "abc123"),
            ("Pure English Channel", "12-31-2025", "xyz789"),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            for creator, date, video_id in test_cases:
                filename = generate_filename(date, creator, video_id)
                filepath = os.path.join(temp_dir, filename)

                # Write a test file
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"Test content for {creator}\n中文测试内容\n")

                # Verify file exists and can be read
                assert os.path.exists(filepath)

                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    assert creator in content or creator.replace(" ", "_") in filename
                    assert "中文测试内容" in content


def test_end_to_end_encoding_workflow():
    """
    End-to-end test: Create JSON with Chinese content, load it, generate filenames,
    and verify everything preserves encoding correctly.
    """
    test_data = {
        "content_resources": [
            {
                "content_creator": "海伦子Hellen",
                "native_lang": "zh",
                "content_collection": [
                    {
                        "video_title": "星舰飞往火星会经历什么?—轨道加注、辐射与着陆的极限挑战",
                        "video_id": "73cdsu6TrbI",
                        "published_time": "11-11-2025",
                        "behind_paywall": False,
                        "downloaded": False
                    }
                ]
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json_file = f.name

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Step 1: Save JSON with Chinese content
            save_content_resources(test_data, json_file)

            # Step 2: Load JSON
            loaded_data = load_content_resources(json_file)

            # Step 3: Generate filename
            creator = loaded_data['content_resources'][0]['content_creator']
            video = loaded_data['content_resources'][0]['content_collection'][0]
            filename = generate_filename(
                video['published_time'],
                creator,
                video['video_id']
            )

            # Step 4: Create a mock transcript file
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"标题: {video['video_title']}\n")
                f.write(f"创作者: {creator}\n")
                f.write("这是一段中文字幕内容\n")
                f.write("This is English subtitle content\n")

            # Step 5: Verify everything
            assert os.path.exists(filepath)

            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "星舰飞往火星" in content
                assert "海伦子Hellen" in content
                assert "这是一段中文字幕内容" in content
                assert "This is English subtitle content" in content

            # Step 6: Update JSON with downloaded flag
            loaded_data['content_resources'][0]['content_collection'][0]['downloaded'] = True
            save_content_resources(loaded_data, json_file)

            # Step 7: Reload and verify
            final_data = load_content_resources(json_file)
            assert final_data['content_resources'][0]['content_collection'][0]['downloaded'] == True
            assert final_data['content_resources'][0]['content_creator'] == "海伦子Hellen"

        finally:
            os.unlink(json_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
