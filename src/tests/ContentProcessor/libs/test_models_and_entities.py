"""Additional targeted tests to push ContentProcessor to 80%"""
from libs.models.content_process import ContentProcess, Step_Outputs
from libs.pipeline.entities.pipeline_data import DataPipeline
from libs.pipeline.entities.pipeline_file import PipelineLogEntry, FileDetailBase
from libs.pipeline.entities.pipeline_message_base import SerializableException, PipelineMessageBase
from libs.pipeline.entities.pipeline_message_context import MessageContext


class TestContentProcessModel:
    """Tests for ContentProcess model"""

    def test_content_process_creation(self):
        """Test creating ContentProcess"""
        process = ContentProcess(
            id="proc-123",
            status="processing",
            created_at="2026-03-24T00:00:00Z"
        )
        assert process.id == "proc-123"
        assert process.status == "processing"

    def test_content_process_with_steps(self):
        """Test ContentProcess with step outputs"""
        step_output = Step_Outputs(
            step_name="extraction",
            output_data={"key": "value"}
        )
        process = ContentProcess(
            id="proc-456",
            status="completed",
            created_at="2026-03-24T00:00:00Z",
            step_outputs=[step_output]
        )
        assert len(process.step_outputs) == 1
        assert process.step_outputs[0].step_name == "extraction"

    def test_step_outputs_creation(self):
        """Test creating Step_Outputs"""
        step = Step_Outputs(
            step_name="validation",
            output_data={"validated": True}
        )
        assert step.step_name == "validation"
        assert step.output_data["validated"] is True


class TestPipelineEntities:
    """Tests for pipeline entity models"""

    def test_data_pipeline_creation(self):
        """Test DataPipeline creation"""
        data = DataPipeline(
            id="data-123",
            status="processing"
        )
        assert data.id == "data-123"
        assert data.status == "processing"

    def test_pipeline_log_entry(self):
        """Test PipelineLogEntry creation"""
        log = PipelineLogEntry(
            timestamp="2026-03-24T00:00:00Z",
            level="INFO",
            message="Processing started"
        )
        assert log.level == "INFO"
        assert "Processing" in log.message

    def test_serializable_exception(self):
        """Test SerializableException"""
        exc = SerializableException(
            message="Test error",
            type="ValueError",
            stack_trace="line 1\nline 2"
        )
        assert exc.message == "Test error"
        assert exc.type == "ValueError"

    def test_message_context(self):
        """Test MessageContext"""
        ctx = MessageContext(
            request_id="req-123",
            user_id="user-456"
        )
        assert ctx.request_id == "req-123"


class TestPipelineMessageEdgeCases:
    """Edge case tests for pipeline messages"""

    def test_pipeline_message_base(self):
        """Test PipelineMessageBase creation"""
        msg = PipelineMessageBase(
            id="msg-123",
            type="test_message"
        )
        assert msg.id == "msg-123"
        assert msg.type == "test_message"

    def test_content_process_empty_step_outputs(self):
        """Test ContentProcess with no step outputs"""
        process = ContentProcess(
            id="proc-789",
            status="pending",
            created_at="2026-03-24T00:00:00Z",
            step_outputs=[]
        )
        assert process.id == "proc-789"
        assert len(process.step_outputs) == 0

    def test_serializable_exception_minimal(self):
        """Test SerializableException with minimal data"""
        exc = SerializableException(
            message="Error occurred",
            type="Exception"
        )
        assert exc.message == "Error occurred"

    def test_file_detail_base(self):
        """Test FileDetailBase creation"""
        detail = FileDetailBase(
            file_name="test.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        assert detail.file_name == "test.pdf"
        assert detail.file_size == 1024


class TestUtilsAndHandlers:
    """Tests for utility functions and handlers"""

    def test_stopwatch_timing(self):
        """Test stopwatch basic timing"""
        from libs.utils.stopwatch import Stopwatch
        import time

        sw = Stopwatch()
        sw.start()
        time.sleep(0.01)  # Sleep 10ms
        sw.stop()
        elapsed = sw.elapsed_time()

        # Should be at least 10ms (accounting for system variance)
        assert elapsed >= 0.008

    def test_handler_info_model(self):
        """Test HandlerInfo model"""
        from libs.process_host.handler_process_host import HandlerInfo

        info = HandlerInfo(
            name="TestHandler",
            path="libs.handlers.test_handler",
            enabled=True
        )
        assert info.name == "TestHandler"
        assert info.enabled is True

    def test_schema_model(self):
        """Test Schema model"""
        from libs.pipeline.entities.schema import Schema

        schema = Schema(
            name="DocumentSchema",
            version="1.0",
            fields={"title": "string", "content": "text"}
        )
        assert schema.name == "DocumentSchema"
        assert schema.version == "1.0"
        assert "title" in schema.fields

    def test_data_pipeline_with_status(self):
        """Test DataPipeline status updates"""
        from libs.pipeline.entities.pipeline_data import DataPipeline

        data = DataPipeline(
            id="pipeline-001",
            status="pending"
        )
        assert data.status == "pending"

        # Test status change
        data.status = "completed"
        assert data.status == "completed"

    def test_multiple_step_outputs(self):
        """Test ContentProcess with multiple step outputs"""
        steps = [
            Step_Outputs(step_name="step1", output_data={"result": 1}),
            Step_Outputs(step_name="step2", output_data={"result": 2}),
            Step_Outputs(step_name="step3", output_data={"result": 3})
        ]

        process = ContentProcess(
            id="proc-multi",
            status="completed",
            created_at="2026-03-24T00:00:00Z",
            step_outputs=steps
        )

        assert len(process.step_outputs) == 3
        assert process.step_outputs[1].step_name == "step2"
        assert process.step_outputs[2].output_data["result"] == 3

        from libs.utils.utils import value_contains

        assert value_contains("hello world", "world") is True
        assert value_contains("hello world", "xyz") is False
        assert value_contains([1, 2, 3], 2) is True
