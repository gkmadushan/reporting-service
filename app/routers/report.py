# coding: utf8
from sqlalchemy.sql.sqltypes import DateTime
from sqlalchemy.exc import IntegrityError
from starlette.responses import Response
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Header
from dependencies import common_params, get_db, get_secret_random
from schemas import CreateReport
from sqlalchemy.orm import Session
from typing import Optional
from models import LessonLearntReport, Reference
from dependencies import get_token_header
import uuid
from datetime import datetime
from exceptions import username_already_exists
from sqlalchemy import over, text
from sqlalchemy import engine_from_config, and_, func, literal_column, case
from sqlalchemy_filters import apply_pagination
import time
import os
import uuid
import json
from sqlalchemy.dialects import postgresql
import base64
import math
from fpdf import FPDF
from fastapi.responses import StreamingResponse
import io
import datetime
import pandas as pd
import os


page_size = os.getenv('PAGE_SIZE')

router = APIRouter(
    prefix="/v1/reports",
    tags=["ReportingAPIs"],
    responses={404: {"description": "Not found"}},
)


@router.get("")
def get_by_filter(page: Optional[str] = 1, limit: Optional[int] = 10, commons: dict = Depends(common_params), db: Session = Depends(get_db), resource: Optional[str] = None, environment: Optional[str] = None):
    sql = f"""
        select
        ROW_NUMBER () OVER (ORDER BY s.started_at) as index,
        s.id,
        s.started_at, s.ended_at,
        r.name as resource, r.ipv4, r.ipv6, r.os,
        e.name as environment, e.description, e.group_id,
        (SELECT count(*) FROM result WHERE scan_id = s.id AND status = True) as issues
        from resource r 
        inner join scan s ON s.reference = r.id and s.id = (SELECT id FROM scan x where x.reference = r.id and x.ended_at is not null order by x.ended_at desc limit 1)
        inner join environment e ON e.id = r.environment_id
        inner join scan_status ss ON ss.id = s.scan_status_id
        WHERE
        ss.code = 'ENDED'        
        """
    if resource:
        sql = sql + f"""and r.id = :resource """
    if environment:
        sql = sql + f"""and e.id = :environment """
    sql = sql + f""" order by s.ended_at desc """
    sql = sql + f""" LIMIT :limit OFFSET(:offset) """

    result = db.execute(text(sql), {"resource": resource, "environment": environment,
                        "limit": limit, "offset": ((int(page)-1) * limit)})
    db.close()

    rows = []
    for row in result:
        rows.append(row)

    # counts
    sql = f"""
        select count(*)
        from resource r 
        inner join scan s ON s.reference = r.id and s.id = (SELECT id FROM scan x where x.reference = r.id and x.ended_at is not null order by x.ended_at desc limit 1)
        inner join environment e ON e.id = r.environment_id
        inner join scan_status ss ON ss.id = s.scan_status_id
        WHERE
        ss.code = 'ENDED'   
        """
    if resource:
        sql = sql + f"""and r.id = '{resource}'"""
    if environment:
        sql = sql + f"""and e.id = '{environment}'"""

    count = db.execute(text(sql)).first()
    db.close()

    response = {
        "data": rows,
        "meta": {
            "total_records": count['count'],
            "limit": limit,
            "num_pages": math.ceil(int(count['count'])/limit),
            "current_page": int(page)
        }
    }

    return response


@router.get("/environments/{id}")
def get_by_id(id: str, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    sql = f"""
        select e.id, e.name,
        (
            SELECT COUNT(*) FROM result r
            INNER JOIN scan s ON s.id = r.scan_id
            INNER JOIN resource res ON res.id = s.reference
            INNER JOIN scan_status ss ON ss.id = s.scan_status_id
            WHERE res.environment_id = e.id and r.status = True and ss.code = 'ENDED'
            and r.score in ('High', 'Critical')
            and s.id in (select id from scan p where p.reference = res.id and p.ended_at is not null order by p.ended_at desc limit 1)
        ) as high,
        (
            SELECT COUNT(*) FROM result r
            INNER JOIN scan s ON s.id = r.scan_id
            INNER JOIN resource res ON res.id = s.reference
            INNER JOIN scan_status ss ON ss.id = s.scan_status_id
            WHERE res.environment_id = e.id and r.status = True and ss.code = 'ENDED'
            and r.score = 'Medium'
            and s.id in (select id from scan p where p.reference = res.id and p.ended_at is not null order by p.ended_at desc limit 1)
        ) as medium,
        (
            SELECT COUNT(*) FROM result r
            INNER JOIN scan s ON s.id = r.scan_id
            INNER JOIN resource res ON res.id = s.reference
            INNER JOIN scan_status ss ON ss.id = s.scan_status_id
            WHERE res.environment_id = e.id and r.status = True and ss.code = 'ENDED'
            and r.score not in ('High', 'Critical','Medium')
            and s.id in (select id from scan p where p.reference = res.id and p.ended_at is not null order by p.ended_at desc limit 1)
        ) as low
        from environment e
        where e.id = :id
        """

    result = db.execute(text(sql), {'id': id})
    db.close()
    scan_details = result.first()

    sql = f"""
        SELECT
        s.id as scan, res.id, res.name, res.ipv4, res.ipv6, res.os, (SELECT COUNT(*) FROM result r WHERE r.scan_id = s.id AND r.status = True) as open_issues
        FROM
        resource res
        INNER JOIN scan s ON s.id = (SELECT x.id FROM scan x INNER JOIN scan_status ss ON ss.id = x.scan_status_id WHERE x.reference = res.id AND ss.code = 'ENDED' ORDER BY x.ended_at desc LIMIT 1)
        WHERE
        res.environment_id = :id

        """

    result = db.execute(text(sql), {'id': id})
    db.close()
    results = []
    for row in result:
        results.append(row)

    class PDF(FPDF):
        def override_header(self, title, completed_at, type, user):
            self.image("./templates/assets/logo.png", w=30, x=10, y=12)
            self.set_font("times", size=15, style='B')
            self.set_xy(0, 8)
            self.cell(287, 10, title, 0, 0, "R")
            self.set_font("times", size=10)
            self.set_xy(0, 13)
            self.cell(287, 10, "Engine: Automated Vulnerability Management System", 0, 0, "R")
            self.line(x1=10, x2=287, y1=28, y2=28)
            self.ln(16)

        def footer(self):
            self.set_y(-15)
            self.set_font("times", size=8)
            self.cell(287, 10,  '© Kingston University | MSc SE Project | Student : K2063482 (GKMC)', 0, 0, 'C')
            self.set_font("times", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", 0, 0, "R")

    pdf = PDF('L', 'mm', 'A4')
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.override_header('Security State Report', '', '', '')
    pdf.set_font("Times", size=12)

    # System info

    pdf.set_font("Times", size=14, style='B')
    pdf.cell(0, 10, 'ENVIRONMENT : '+scan_details.name+'')
    pdf.set_fill_color(240, 92, 62)
    pdf.rect(x=10, y=40, w=55, h=30, style="FD")
    pdf.set_xy(10, 60)
    pdf.set_font("Times", size=14, style='B')
    pdf.cell(55, 10,  'HIGH', 1, 0, 'C')
    pdf.set_xy(10, 40)
    pdf.set_font("Times", size=35, style='B')
    pdf.set_text_color(255, 255, 255)
    pdf.cell(55, 20,  str(scan_details.high), 1, 0, 'C')
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(240, 151, 62)
    pdf.rect(x=77, y=40, w=55, h=30, style="FD")
    pdf.set_xy(77, 60)
    pdf.set_font("Times", size=14, style='B')
    pdf.cell(55, 10,  'MEDIUM', 1, 0, 'C')
    pdf.set_xy(77, 40)
    pdf.set_font("Times", size=35, style='B')
    pdf.set_text_color(255, 255, 255)
    pdf.cell(55, 20,  str(scan_details.medium), 1, 0, 'C')
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(62, 184, 240)
    pdf.rect(x=144, y=40, w=55, h=30, style="FD")
    pdf.set_xy(144, 60)
    pdf.set_font("Times", size=14, style='B')
    pdf.cell(55, 10,  'LOW', 1, 0, 'C')
    pdf.set_xy(144, 40)
    pdf.set_font("Times", size=35, style='B')
    pdf.set_text_color(255, 255, 255)
    pdf.cell(55, 20,  str(scan_details.low), 1, 0, 'C')
    pdf.set_xy(200, 40)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Times", size=10)
    pdf.set_fill_color(255, 255, 255)
    pdf.multi_cell(
        85, 5,  'These indicators shows open issue count out of the detected issues. Work in progress counts will be showing individually in the below table. Issues reported in **HIGH** and **MEDIUM** issues should be fixed immidiately.', 0, 'J', markdown=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(10, 60)
    pdf.ln(15)
    pdf.set_font("Times", size=14, style='B')
    pdf.cell(0, 10, 'RESOURCES')
    pdf.ln(13)

    pdf.set_font("Times", size=12)
    pdf.cell(115, 8, 'RESOURCE NAME', 1, 0, 'C')
    pdf.cell(60, 8, 'IP ADDRESS', 1, 0, 'C')
    pdf.cell(60, 8, 'OS', 1, 0, 'C')
    pdf.cell(40, 8, 'OPEN ISSUES', 1, 0, 'C')
    pdf.ln(8)
    for res in results:
        pdf.set_font("Times", size=12)
        pdf.cell(115, 8, res.name, 1, 0, 'L')
        pdf.cell(60, 8, res.ipv4+' '+res.ipv6, 1, 0)
        pdf.cell(60, 8, res.os, 1, 0, 'C')
        pdf.cell(40, 8, str(res.open_issues), 1, 0, 'C')
        pdf.ln(8)

    pdf_output = io.BytesIO(bytes(pdf.output(dest='S')))

    return StreamingResponse(pdf_output, media_type='application/pdf')


@router.get("/scans/{id}")
def get_by_id(id: str, accept: Optional[str] = Header(None), commons: dict = Depends(common_params), db: Session = Depends(get_db)):

    sql = f"""
        select r.id, r.scan_id, c.name as class_name, r.title, r.description, r.score, r.fix_available, r.impact
        from result r
        inner join class c ON c.id = r.class_id
        where
        r.scan_id = :id AND
        r.status = True AND
        c.code != 'inventory'
        order by CASE
            WHEN r.score = 'High' THEN 1
            WHEN r.score = 'Medium' THEN 2
            WHEN r.score = 'Low' THEN 3
            ELSE 4
            END ASC
        """

    result = db.execute(text(sql), {'id': id})
    db.close()

    sql = f"""
        select
        s.started_at, s.ended_at, s.created_by as created_by,
        r.name as resource, r.ipv4, r.ipv6, r.os,
        e.name as environment, e.description, e.group_id,
        (SELECT count(*) FROM result WHERE scan_id = s.id AND status = True AND score in ('High', 'Critical')) as high_sev_issues,
        (SELECT count(*) FROM result WHERE scan_id = s.id AND status = True AND score = 'Medium') as medium_sev_issues,
        (SELECT count(*) FROM result WHERE scan_id = s.id AND status = True AND score not in ('High', 'Critical', 'Medium')) as low_sev_issues
        from scan s
        inner join resource r ON r.id = s.reference
        inner join environment e ON e.id = r.environment_id
        inner join scan_status ss ON ss.id = s.scan_status_id
        WHERE
        s.id = '{id}'
        """

    scan = db.execute(text(sql))
    db.close()

    results = []
    excel_data = []

    for row in result:
        data = {'references': []}
        sql = f"""select * from reference where result_id = '{row['id']}'"""
        references = db.execute(text(sql))
        for ref in references:
            data['info'] = row
            data['references'].append(ref)
        results.append(data)
        excel_data.append({'type': row['class_name'], 'title': row['title'],
                          'description': row['description'], 'severity': row['score']})

    if(accept == 'application/xlsx'):
        buffer = io.BytesIO()
        df = pd.DataFrame(excel_data)
        with pd.ExcelWriter(buffer) as writer:
            df.to_excel(writer)
        return Response(content=bytes(buffer.getbuffer()), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    else:

        scan_details = scan.first()

        if scan_details.created_by == None:
            scan_type = 'AUTOMATIC'
            created_by = 'System'
        else:
            scan_type = 'MANUAL'
            created_by = scan_details.created_by

        class PDF(FPDF):
            def override_header(self, title, completed_at, type, user):
                self.image("./templates/assets/logo.png", w=30, x=10, y=12)
                self.set_font("times", size=15, style='B')
                self.set_xy(0, 8)
                self.cell(200, 10, title, 0, 0, "R")
                self.set_font("times", size=10)
                self.set_xy(0, 13)
                self.cell(200, 10, "Engine: Automated Vulnerability Management System", 0, 0, "R")
                self.set_y(16)
                self.cell(190, 10, "Scan completed at: "+completed_at, 0, 0, "R")
                self.set_y(19)
                self.cell(190, 10, "Type: " + type + " | User : "+user, 0, 0, "R")
                self.line(x1=10, x2=200, y1=28, y2=28)
                self.ln(10)

            def footer(self):
                self.set_y(-15)
                self.set_font("times", size=8)
                self.cell(200, 10,  '© Kingston University | MSc SE Project | Student : K2063482 (GKMC)', 0, 0, 'C')
                self.set_font("times", "I", 8)
                self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", 0, 0, "R")

        pdf = PDF('P', 'mm', 'A4')
        # pdf.add_font('DejaVu', fname=os.path.join('/usr/share/fonts/truetype/dejavu', 'DejaVuSans.ttf'), uni=True)
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.override_header('Vulnerability Scan Report', (scan_details.ended_at-datetime.timedelta(hours=+5.5)).strftime(
            "%Y/%m/%d %I:%M %p"), scan_type, created_by)
        pdf.set_font("Times", size=12)

        # System info
        pdf.set_font("Times", size=14, style='B')
        pdf.cell(0, 10, 'RESOURCE DETAILS')
        pdf.set_font("Times", size=12)
        pdf.ln(5)
        pdf.cell(0, 10, 'Environment: '+scan_details.environment)
        pdf.ln(5)
        pdf.cell(0, 10, 'Resource name: '+scan_details.resource)
        pdf.ln(5)
        pdf.cell(0, 10, 'IP address: '+scan_details.ipv4+' '+scan_details.ipv6)
        pdf.ln(5)
        pdf.set_font("Times", size=30)
        pdf.set_xy(100, 30)
        pdf.cell(100, 10, 'OS:'+scan_details.os.capitalize(), 0, 0, 'R')
        pdf.ln(5)
        pdf.set_font("Times", size=14, style='B')
        pdf.set_xy(0, 48)
        pdf.ln(4)
        pdf.set_font("Times", size=14, style='B')
        pdf.cell(0, 10, 'SUMMARY')
        pdf.set_fill_color(240, 92, 62)
        pdf.rect(x=10, y=60, w=55, h=30, style="FD")
        pdf.set_xy(10, 80)
        pdf.set_font("Times", size=14, style='B')
        pdf.cell(55, 10,  'HIGH', 1, 0, 'C')
        pdf.set_xy(10, 60)
        pdf.set_font("Times", size=35, style='B')
        pdf.set_text_color(255, 255, 255)
        pdf.cell(55, 20,  str(scan_details.high_sev_issues), 1, 0, 'C')
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(240, 151, 62)
        pdf.rect(x=77, y=60, w=55, h=30, style="FD")
        pdf.set_xy(77, 80)
        pdf.set_font("Times", size=14, style='B')
        pdf.cell(55, 10,  'MEDIUM', 1, 0, 'C')
        pdf.set_xy(77, 60)
        pdf.set_font("Times", size=35, style='B')
        pdf.set_text_color(255, 255, 255)
        pdf.cell(55, 20,  str(scan_details.medium_sev_issues), 1, 0, 'C')
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(62, 184, 240)
        pdf.rect(x=144, y=60, w=55, h=30, style="FD")
        pdf.set_xy(144, 80)
        pdf.set_font("Times", size=14, style='B')
        pdf.cell(55, 10,  'LOW', 1, 0, 'C')
        pdf.set_xy(144, 60)
        pdf.set_font("Times", size=35, style='B')
        pdf.set_text_color(255, 255, 255)
        pdf.cell(55, 20,  str(scan_details.low_sev_issues), 1, 0, 'C')
        pdf.set_text_color(0, 0, 0)
        pdf.set_xy(10, 80)
        pdf.ln(15)
        pdf.set_font("Times", size=14, style='B')
        pdf.cell(0, 10, 'VULNERABILITY DETAILS')
        pdf.ln(13)

        pdf.set_font("Times", size=12)
        pdf.cell(30, 8, 'SEVERITY', 1, 0, 'C')
        pdf.cell(120, 8, 'ISSUE TITLE', 1, 0, 'C')
        pdf.cell(40, 8, 'TYPE', 1, 0, 'C')
        pdf.ln(8)
        for res in results:
            pdf.set_font("Times", size=12)
            if 'info' in res.keys():
                pdf.cell(30, 8, res['info']['score'], 1, 0, 'C')
                pdf.cell(120, 8, res['info']['title'], 1, 0)
                pdf.cell(40, 8, res['info']['class_name'], 1, 0, 'C')
                pdf.ln(8)

        pdf.add_page()
        pdf.set_font("Times", size=15, style='B')
        pdf.cell(0, 10, 'DEVOPS INFO')
        pdf.ln(8)
        for res in results:
            if 'info' in res.keys():
                pdf.set_font("Times", size=12, style="B")
                pdf.cell(30, 8, res['info']['title']+' ({})'.format(res['info']['class_name']), 0, 0)
                pdf.ln(8)
                pdf.set_font("Times", size=12)
                pdf.multi_cell(190, 5, res['info']['description'].encode(
                    'latin-1', 'replace').decode('latin-1'), 0, 'J')
                pdf.ln(1)

            if 'references' in res.keys():
                pdf.set_font("Times", size=12)
                for referance in res['references']:
                    pdf.cell(30, 8, referance['type_code']+' '+referance['code'], 0, 0)
                    if referance['url'] != None:
                        pdf.set_font("Times", size=12, style="U")
                        pdf.ln(4)
                        pdf.cell(30, 8, referance['url'].encode(
                            'latin-1', 'replace').decode('latin-1'), 0, 0)
                    pdf.ln(8)
            pdf.ln(8)

        pdf_output = io.BytesIO(bytes(pdf.output(dest='S')))

        return StreamingResponse(pdf_output, media_type='application/pdf')
